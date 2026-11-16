import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from sipl.parser import SiplSyntaxError
from sipl.visualization import ast_tree, compare, parse_tree, to_dot, to_html, to_svg, to_text

ROOT = Path(__file__).parent.parent
PROGRAMS = sorted((ROOT / "examples").glob("*.sipl")) + sorted((ROOT / "tests" / "grammar" / "valid").glob("*.sipl"))


def _nodes(node):
    yield node
    for child in node.get("children", []):
        yield from _nodes(child)


def _leaves(node):
    return [n["text"] for n in _nodes(node) if "children" not in n]


def _symbols(node):
    return [child["symbol"] for child in node["children"]]


def test_small_tree():
    assert parse_tree("begin x := 1 end") == {
        "symbol": "program", "text": "begin x := 1 end",
        "span": {"line": 1, "column": 1, "end_line": 1, "end_column": 17},
        "children": [
            {"symbol": "begin", "text": "begin", "span": {"line": 1, "column": 1, "end_line": 1, "end_column": 6}},
            {"symbol": "stmt_seq", "text": "x := 1",
             "span": {"line": 1, "column": 7, "end_line": 1, "end_column": 13},
             "children": [
                 {"symbol": "stmt", "text": "x := 1",
                  "span": {"line": 1, "column": 7, "end_line": 1, "end_column": 13},
                  "children": [
                      {"symbol": "assign", "text": "x := 1",
                       "span": {"line": 1, "column": 7, "end_line": 1, "end_column": 13},
                       "children": [
                           {"symbol": "NAME", "text": "x",
                            "span": {"line": 1, "column": 7, "end_line": 1, "end_column": 8}},
                           {"symbol": ":=", "text": ":=",
                            "span": {"line": 1, "column": 9, "end_line": 1, "end_column": 11}},
                           {"symbol": "aexpr", "text": "1",
                            "span": {"line": 1, "column": 12, "end_line": 1, "end_column": 13},
                            "children": [
                                {"symbol": "aterm", "text": "1",
                                 "span": {"line": 1, "column": 12, "end_line": 1, "end_column": 13},
                                 "children": [
                                     {"symbol": "afactor", "text": "1",
                                      "span": {"line": 1, "column": 12, "end_line": 1, "end_column": 13},
                                      "children": [
                                          {"symbol": "NUMBER", "text": "1",
                                           "span": {"line": 1, "column": 12, "end_line": 1, "end_column": 13}},
                                      ]},
                                 ]},
                            ]},
                       ]},
                  ]},
             ]},
            {"symbol": "end", "text": "end", "span": {"line": 1, "column": 14, "end_line": 1, "end_column": 17}},
        ],
    }


@pytest.mark.parametrize("path", PROGRAMS, ids=lambda p: p.name)
def test_leaves_spell_the_program(path):
    source = path.read_text(encoding="utf-8")
    assert "".join(_leaves(parse_tree(source))) == "".join(source.split())


@pytest.mark.parametrize("path", PROGRAMS, ids=lambda p: p.name)
def test_every_node_points_to_its_source(path):
    source = path.read_text(encoding="utf-8")
    lines = source.splitlines()
    for node in _nodes(parse_tree(source)):
        span = node["span"]
        if span["line"] == span["end_line"]:
            assert lines[span["line"] - 1][span["column"] - 1:span["end_column"] - 1] == node["text"]
        else:
            assert node["text"].startswith(lines[span["line"] - 1][span["column"] - 1:])


def test_precedence_is_visible_in_tree():
    assign = parse_tree("begin x := 1 + 2 * 3 end")["children"][1]["children"][0]["children"][0]
    aexpr = assign["children"][2]
    assert _symbols(aexpr) == ["aexpr", "+", "aterm"]
    assert _symbols(aexpr["children"][2]) == ["aterm", "*", "afactor"]


def test_sequence_keeps_semicolons():
    stmt_seq = parse_tree("begin x := 1; skip end")["children"][1]
    assert _symbols(stmt_seq) == ["stmt", ";", "stmt"]


def test_syntax_error():
    with pytest.raises(SiplSyntaxError):
        parse_tree("begin end")


def test_text():
    assert to_text(parse_tree("begin skip end")).splitlines() == [
        "<program>  [1:1-1:15]",
        "  begin  [1:1-1:6]",
        "  <stmt_seq>  [1:7-1:11]",
        "    <stmt>  [1:7-1:11]",
        "      <skip_stmt>  [1:7-1:11]",
        "        skip  [1:7-1:11]",
        "  end  [1:12-1:15]",
    ]


def test_dot():
    tree = parse_tree("begin x := 1 end")
    dot = to_dot(tree)
    count = len(list(_nodes(tree)))
    assert dot.startswith("digraph parse_tree {") and dot.endswith("}")
    assert dot.count("shape=") == count
    assert dot.count(" -> ") == count - 1
    assert 'n0 [label="<program>", shape=ellipse, tooltip="1:1-1:17: begin x := 1 end"];' in dot
    assert '[label="NAME x", shape=box, tooltip="1:7-1:8: x"];' in dot


def test_svg():
    tree = parse_tree("begin if ¬ (x > 1) ∨ x = 0 then skip else skip end")
    svg = ET.fromstring(to_svg(tree))
    ns = "{http://www.w3.org/2000/svg}"
    count = len(list(_nodes(tree)))
    assert len(svg.findall(f"{ns}text")) == count
    assert len(svg.findall(f"{ns}line")) == count - 1
    titles = [t.text for t in svg.iter(f"{ns}title")]
    assert "1:12-1:13: (" in titles
    assert "1:7-1:9: if" in titles


def test_ast_tree():
    assert ast_tree("begin x := 1 + y end") == {
        "symbol": "Program", "text": "begin x := 1 + y end",
        "span": {"line": 1, "column": 1, "end_line": 1, "end_column": 21},
        "children": [
            {"symbol": "Assign x", "text": "x := 1 + y",
             "span": {"line": 1, "column": 7, "end_line": 1, "end_column": 17},
             "children": [
                 {"symbol": "BinOp +", "text": "1 + y",
                  "span": {"line": 1, "column": 12, "end_line": 1, "end_column": 17},
                  "children": [
                      {"symbol": "Num 1", "text": "1",
                       "span": {"line": 1, "column": 12, "end_line": 1, "end_column": 13}, "children": []},
                      {"symbol": "Var y", "text": "y",
                       "span": {"line": 1, "column": 16, "end_line": 1, "end_column": 17}, "children": []},
                  ]},
             ]},
        ],
    }


def test_ast_tree_multiline_fragment():
    seq = ast_tree("begin\n  x := 1;\n  y := 2\nend")["children"][0]
    assert seq["symbol"] == "Seq"
    assert seq["text"] == "x := 1;\n  y := 2"


@pytest.mark.parametrize("path", PROGRAMS, ids=lambda p: p.name)
def test_every_ast_node_has_parse_tree_node(path):
    source = path.read_text(encoding="utf-8")
    tree_spans = {(n["text"], str(n["span"])) for n in _nodes(parse_tree(source))}
    for node in _nodes(ast_tree(source)):
        if node["symbol"] != "Seq":
            assert (node["text"], str(node["span"])) in tree_spans


def test_compare():
    source = "begin x := 1 + 2 end"
    assert compare(parse_tree(source), ast_tree(source)) == {
        "parse_tree": {"nodes": 17, "depth": 9},
        "ast": {"nodes": 5, "depth": 4},
        "only_in_parse_tree": ["+", ":=", "NAME x", "begin", "end"],
    }


def test_html():
    source = "begin x := 1 + 2 end"
    tree, ast = parse_tree(source), ast_tree(source)
    page = to_html(tree, ast)
    assert page.startswith("<!doctype html>")
    assert page.count("<svg ") == 2
    assert page.count('data-span="1:12-1:17"') == 2
    assert "<td>вузлів</td><td>17</td><td>5</td>" in page
    assert ">BinOp +</text>" in page and "&lt;aexpr&gt;</text>" in page
