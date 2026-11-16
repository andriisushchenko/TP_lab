import itertools
import json
from html import escape

from lark import Token

from sipl.ast import to_dict
from sipl.grammar import tree_parser
from sipl.parser import parse


def _span(item):
    return {"line": item.line, "column": item.column, "end_line": item.end_line, "end_column": item.end_column}


def _node(item, source):
    if isinstance(item, Token):
        symbol = item.type if item.type in ("NAME", "NUMBER") else str(item)
        return {"symbol": symbol, "text": str(item), "span": _span(item)}
    meta = item.meta
    return {
        "symbol": str(item.data),
        "text": source[meta.start_pos:meta.end_pos],
        "span": _span(meta),
        "children": [_node(child, source) for child in item.children],
    }


def parse_tree(source):
    parse(source)
    return _node(tree_parser.parse(source), source)


def _offset(source, line, column):
    return len("".join(source.splitlines(keepends=True)[:line - 1])) + column - 1


def _ast_node(node, source):
    span = node["span"]
    start = _offset(source, span["line"], span["column"])
    end = _offset(source, span["end_line"], span["end_column"])
    values = [str(v) for k, v in node.items() if k not in ("type", "span") and not isinstance(v, (dict, list))]
    children = []
    for value in node.values():
        if isinstance(value, dict) and "type" in value:
            children.append(value)
        elif isinstance(value, list):
            children.extend(value)
    return {
        "symbol": " ".join([node["type"], *values]),
        "text": source[start:end],
        "span": span,
        "children": [_ast_node(child, source) for child in children],
    }


def ast_tree(source):
    return _ast_node(to_dict(parse(source)), source)


def label(node):
    if "children" in node:
        return f"<{node['symbol']}>"
    if node["symbol"] == node["text"]:
        return node["text"]
    return f"{node['symbol']} {node['text']}"


def where(node):
    span = node["span"]
    return f"{span['line']}:{span['column']}-{span['end_line']}:{span['end_column']}"


def to_text(tree):
    lines = []

    def add(node, depth):
        lines.append(f"{'  ' * depth}{label(node)}  [{where(node)}]")
        for child in node.get("children", []):
            add(child, depth + 1)

    add(tree, 0)
    return "\n".join(lines)


def to_dot(tree):
    lines = ["digraph parse_tree {"]
    ids = itertools.count()

    def add(node):
        name = f"n{next(ids)}"
        shape = "ellipse" if "children" in node else "box"
        text = json.dumps(label(node), ensure_ascii=False)
        tooltip = json.dumps(f"{where(node)}: {node['text']}", ensure_ascii=False)
        lines.append(f"  {name} [label={text}, shape={shape}, tooltip={tooltip}];")
        for child in node.get("children", []):
            lines.append(f"  {name} -> {add(child)};")
        return name

    add(tree)
    lines.append("}")
    return "\n".join(lines)


def to_svg(tree, label_of=label):
    edges, labels = [], []
    right, bottom = 0, 0

    def place(node, depth):
        nonlocal right, bottom
        y = 30 + depth * 60
        bottom = max(bottom, y)
        if node.get("children"):
            xs = [place(child, depth + 1) for child in node["children"]]
            x = (xs[0] + xs[-1]) / 2
            for child_x in xs:
                edges.append(f'<line x1="{x}" y1="{y + 6}" x2="{child_x}" y2="{y + 46}" stroke="#999"/>')
            color = "#1f4e9e"
        else:
            width = max(100, 8 * len(label_of(node)) + 10)
            x = right + width / 2
            right += width
            color = "#b00000"
        labels.append(
            f'<text x="{x}" y="{y}" fill="{color}" data-span="{where(node)}">'
            f'<title>{escape(where(node))}: {escape(node["text"])}</title>{escape(label_of(node))}</text>'
        )
        return x

    place(tree, 0)
    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{right}" height="{bottom + 20}" '
        'font-family="monospace" font-size="12" text-anchor="middle">',
        '<rect width="100%" height="100%" fill="white"/>',
        *edges,
        *labels,
        "</svg>",
    ])


def _nodes(node):
    yield node
    for child in node.get("children", []):
        yield from _nodes(child)


def _depth(node):
    return 1 + max((_depth(child) for child in node.get("children", [])), default=0)


def compare(tree, ast):
    ast_spans = {where(node) for node in _nodes(ast)}
    tree_nodes = list(_nodes(tree))
    return {
        "parse_tree": {"nodes": len(tree_nodes), "depth": _depth(tree)},
        "ast": {"nodes": len(list(_nodes(ast))), "depth": _depth(ast)},
        "only_in_parse_tree": sorted({label(n) for n in tree_nodes if where(n) not in ast_spans}),
    }


HTML = """<!doctype html>
<html lang="uk">
<head>
<meta charset="utf-8">
<title>Parse tree ↔ AST</title>
<style>
body {{ font-family: sans-serif; margin: 16px; }}
section {{ overflow-x: auto; border: 1px solid #ccc; margin-bottom: 16px; }}
text {{ cursor: pointer; }}
text.hit {{ fill: #e67e00; font-weight: bold; }}
</style>
</head>
<body>
<h1>Parse tree ↔ AST</h1>
<pre>{source}</pre>
<table border="1" cellpadding="4">
<tr><th></th><th>Parse tree</th><th>AST</th></tr>
<tr><td>вузлів</td><td>{tree_nodes}</td><td>{ast_nodes}</td></tr>
<tr><td>глибина</td><td>{tree_depth}</td><td>{ast_depth}</td></tr>
</table>
<p>Вузли parse tree, для яких в AST немає вузла з тим самим фрагментом коду: {only}</p>
<p>Наведіть мишку на вузол: підсвітяться вузли обох дерев, виведені з того самого фрагмента коду.</p>
<h2>Parse tree (конкретний синтаксис)</h2>
<section>{tree_svg}</section>
<h2>AST (абстрактний синтаксис)</h2>
<section>{ast_svg}</section>
<script>
for (const node of document.querySelectorAll("text[data-span]")) {{
  const same = document.querySelectorAll(`text[data-span="${{node.dataset.span}}"]`);
  node.addEventListener("mouseenter", () => same.forEach(n => n.classList.add("hit")));
  node.addEventListener("mouseleave", () => same.forEach(n => n.classList.remove("hit")));
}}
</script>
</body>
</html>"""


def to_html(tree, ast):
    stats = compare(tree, ast)
    return HTML.format(
        source=escape(tree["text"]),
        tree_nodes=stats["parse_tree"]["nodes"],
        ast_nodes=stats["ast"]["nodes"],
        tree_depth=stats["parse_tree"]["depth"],
        ast_depth=stats["ast"]["depth"],
        only=escape(", ".join(stats["only_in_parse_tree"])),
        tree_svg=to_svg(tree),
        ast_svg=to_svg(ast, lambda node: node["symbol"]),
    )
