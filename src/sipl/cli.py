import argparse
import json
import sys
from pathlib import Path

from sipl.ast import to_dict as ast_to_dict
from sipl.interpreter import MAX_ITERATIONS, SiplRuntimeError, run
from sipl.interpreter.events import to_dict as event_to_dict
from sipl.parser import SiplSyntaxError, parse
from sipl.visualization import ast_tree, compare, parse_tree, to_dot, to_html, to_svg
from sipl.visualization import to_text as tree_to_text

EXIT_OK = 0
EXIT_SYNTAX = 1
EXIT_USAGE = 2
EXIT_RUNTIME = 3

TREE_FORMATS = {"text": tree_to_text, "dot": to_dot, "svg": to_svg}


class UsageError(Exception):
    pass


def _read(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError as e:
        raise UsageError(f"не вдалося прочитати файл '{path}': {e.strerror}") from None


def _state(pairs):
    state = {}
    for pair in pairs:
        name, sep, value = pair.partition("=")
        if not sep or not name:
            raise UsageError(f"очікувалось ЗМІННА=ЧИСЛО, отримано '{pair}'")
        try:
            state[name] = int(value)
        except ValueError:
            raise UsageError(f"'{value}' не є цілим числом (у '{pair}')") from None
    return state


def _limit(args):
    return None if args.max_iterations == 0 else args.max_iterations


def cmd_parse(args, out):
    out["ast"] = ast_to_dict(parse(_read(args.file)))


def cmd_check(args, out):
    parse(_read(args.file))


def cmd_run(args, out):
    program = parse(_read(args.file))
    out["state"] = run(program, _state(args.state), _limit(args))


def cmd_trace(args, out):
    program = parse(_read(args.file))
    state = _state(args.state)
    out["events"] = []
    run(program, state, _limit(args), on_event=lambda e: out["events"].append(event_to_dict(e)))


def cmd_tree(args, out):
    out["tree"] = parse_tree(_read(args.file))


def cmd_compare(args, out):
    source = _read(args.file)
    out["tree"] = parse_tree(source)
    out["ast_tree"] = ast_tree(source)
    out["comparison"] = compare(out["tree"], out["ast_tree"])


def _where(span):
    return "" if span is None else f"[{span['line']}:{span['column']}]"


def _tree_lines(node, depth):
    fields = [f"{k}={v!r}" for k, v in node.items() if k not in ("type", "span") and not isinstance(v, (dict, list))]
    yield "  " * depth + " ".join([node["type"], *fields, _where(node["span"])])
    for value in node.values():
        if isinstance(value, dict) and "type" in value:
            yield from _tree_lines(value, depth + 1)
        elif isinstance(value, list):
            for item in value:
                yield from _tree_lines(item, depth + 1)


def _event_line(event):
    fields = [f"{k}={v!r}" for k, v in event.items() if k not in ("event", "span")]
    return " ".join([f"{_where(event.get('span')):<8}", event["event"], *fields])


def text_parse(out, args):
    return "\n".join(_tree_lines(out["ast"], 0))


def text_check(out, args):
    return "OK: програма синтаксично коректна"


def text_run(out, args):
    return "\n".join(f"{name} = {value}" for name, value in out["state"].items())


def text_trace(out, args):
    return "\n".join(_event_line(e) for e in out["events"])


def text_tree(out, args):
    return TREE_FORMATS[args.format](out["tree"])


def text_compare(out, args):
    return to_html(out["tree"], out["ast_tree"])


COMMANDS = {
    "parse": (cmd_parse, text_parse, "розібрати програму і показати AST"),
    "check": (cmd_check, text_check, "перевірити синтаксис"),
    "run": (cmd_run, text_run, "виконати програму і показати кінцевий стан"),
    "trace": (cmd_trace, text_trace, "виконати програму і показати всі події"),
    "tree": (cmd_tree, text_tree, "показати дерево синтаксичного виводу"),
    "compare": (cmd_compare, text_compare, "HTML-порівняння дерева виводу та AST"),
}


def build_parser():
    parser = argparse.ArgumentParser(prog="sipl", description="Інструменти для мови SIPL")
    commands = parser.add_subparsers(dest="command", required=True)
    for name, (_, _, help_text) in COMMANDS.items():
        command = commands.add_parser(name, help=help_text)
        command.add_argument("file", help="шлях до .sipl-файлу")
        command.add_argument("--json", action="store_true", help="вивести результат у JSON")
        if name in ("run", "trace"):
            command.add_argument("state", nargs="*", metavar="ЗМІННА=ЧИСЛО", help="початковий стан")
            command.add_argument(
                "--max-iterations", type=int, default=MAX_ITERATIONS,
                help=f"ліміт ітерацій циклів, 0 — без ліміту (типово {MAX_ITERATIONS})",
            )
        if name == "tree":
            command.add_argument("--format", choices=TREE_FORMATS, default="text", help="формат дерева")
        if name in ("tree", "compare"):
            command.add_argument("-o", "--output", help="записати результат у файл (UTF-8)")
    return parser


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    args = build_parser().parse_args(argv)
    handler, to_text, _ = COMMANDS[args.command]
    out = {}
    code, error = EXIT_OK, None
    try:
        handler(args, out)
    except UsageError as e:
        code, error = EXIT_USAGE, {"kind": "usage", "message": str(e), "line": None, "column": None}
    except SiplSyntaxError as e:
        code, error = EXIT_SYNTAX, {"kind": "syntax", "message": e.message, "line": e.line, "column": e.column}
    except SiplRuntimeError as e:
        line = e.span.line if e.span else None
        column = e.span.column if e.span else None
        code, error = EXIT_RUNTIME, {"kind": "runtime", "message": e.message, "line": line, "column": column}

    if args.json:
        result = {"ok": code == EXIT_OK, "command": args.command, **out}
        if error is not None:
            result["error"] = error
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if code == EXIT_OK and getattr(args, "output", None):
            Path(args.output).write_text(to_text(out, args) + "\n", encoding="utf-8")
        elif code == EXIT_OK or out:
            print(to_text(out, args))
        if error is not None:
            print(f"Помилка: {_format_error(error)}", file=sys.stderr)
    return code


def _format_error(error):
    if error["line"] is None:
        return error["message"]
    return f"Рядок {error['line']}, колонка {error['column']}: {error['message']}"
