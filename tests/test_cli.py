import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from sipl.cli import EXIT_OK, EXIT_RUNTIME, EXIT_SYNTAX, EXIT_USAGE, main

POWER = str(Path(__file__).parent.parent / "examples" / "power.sipl")


@pytest.fixture
def sipl(capsys):
    def call(*args):
        code = main(list(args))
        captured = capsys.readouterr()
        return code, captured.out, captured.err
    return call


@pytest.fixture
def source(tmp_path):
    def write(text):
        path = tmp_path / "program.sipl"
        path.write_text(text, encoding="utf-8")
        return str(path)
    return write


def test_parse_text(sipl):
    code, out, _ = sipl("parse", POWER)
    assert code == EXIT_OK
    assert out.splitlines()[:4] == [
        "Program [1:1]",
        "  Seq [2:3]",
        "    Assign name='R' [2:3]",
        "      Num value=1 [2:8]",
    ]


def test_parse_json(sipl):
    code, out, _ = sipl("parse", POWER, "--json")
    data = json.loads(out)
    assert code == EXIT_OK
    assert data["ok"] is True and data["command"] == "parse"
    first = data["ast"]["body"]["statements"][0]
    assert first == {
        "type": "Assign",
        "span": {"line": 2, "column": 3, "end_line": 2, "end_column": 9},
        "name": "R",
        "expr": {"type": "Num", "span": {"line": 2, "column": 8, "end_line": 2, "end_column": 9}, "value": 1},
    }


def test_check_ok(sipl):
    assert sipl("check", POWER) == (EXIT_OK, "OK: програма синтаксично коректна\n", "")


def test_check_syntax_error(sipl, source):
    code, out, err = sipl("check", source("begin x := 1 y := 2 end"))
    assert code == EXIT_SYNTAX
    assert out == ""
    assert err.startswith("Помилка: Рядок 1, колонка 14: неочікуване 'y'")


def test_check_syntax_error_json(sipl, source):
    code, out, _ = sipl("check", source("begin x = 1 end"), "--json")
    assert code == EXIT_SYNTAX
    assert json.loads(out) == {
        "ok": False,
        "command": "check",
        "error": {"kind": "syntax", "message": "неочікуване '='; очікувалось: ':='", "line": 1, "column": 9},
    }


def test_run_text(sipl):
    assert sipl("run", POWER, "X=2", "Y=10") == (EXIT_OK, "X = 2\nY = 0\nR = 1024\n", "")


def test_run_json(sipl):
    code, out, _ = sipl("run", POWER, "X=3", "Y=2", "--json")
    assert code == EXIT_OK
    assert json.loads(out) == {"ok": True, "command": "run", "state": {"X": 3, "Y": 0, "R": 9}}


def test_run_negative_input(sipl, source):
    code, out, _ = sipl("run", source("begin y := x * 2 end"), "x=-4")
    assert (code, out) == (EXIT_OK, "x = -4\ny = -8\n")


def test_run_runtime_error(sipl, source):
    code, out, err = sipl("run", source("begin x := y end"), "--json")
    assert code == EXIT_RUNTIME
    assert json.loads(out)["error"] == {
        "kind": "runtime", "message": "змінна 'y' не визначена", "line": 1, "column": 12,
    }


def test_run_runtime_error_text(sipl, source):
    code, out, err = sipl("run", source("begin x := 1 div 0 end"))
    assert (code, out) == (EXIT_RUNTIME, "")
    assert err == "Помилка: Рядок 1, колонка 12: ділення на нуль (div)\n"


def test_max_iterations(sipl, source):
    loop = source("begin while 1 = 1 do skip end")
    code, _, err = sipl("run", loop, "--max-iterations", "5")
    assert code == EXIT_RUNTIME
    assert "ліміт у 5 ітерацій" in err


def test_max_iterations_zero_means_no_limit(sipl, source):
    counter = source("begin i := 0; while 200 > i do i := i + 1 end")
    assert sipl("run", counter, "--max-iterations", "0") == (EXIT_OK, "i = 200\n", "")
    assert sipl("run", counter, "--max-iterations", "10")[0] == EXIT_RUNTIME


def test_trace_text(sipl, source):
    code, out, _ = sipl("trace", source("begin x := 1 end"))
    assert code == EXIT_OK
    assert out.splitlines() == [
        "[1:7]    BeforeStatement statement='Assign'",
        "[1:7]    VariableChanged name='x' old=None new=1",
        "[1:7]    AfterStatement statement='Assign'",
        "         Finished state={'x': 1}",
    ]


def test_trace_json(sipl):
    code, out, _ = sipl("trace", POWER, "X=2", "Y=1", "--json")
    data = json.loads(out)
    assert code == EXIT_OK and data["ok"] is True
    assert data["events"][0]["event"] == "BeforeStatement"
    assert data["events"][-1] == {"event": "Finished", "state": {"X": 2, "Y": 0, "R": 2}}


def test_trace_keeps_events_on_error(sipl, source):
    code, out, err = sipl("trace", source("begin x := 1; y := z end"), "--json")
    data = json.loads(out)
    assert code == EXIT_RUNTIME
    assert data["ok"] is False
    assert data["events"][-1]["event"] == "Failed"
    assert data["error"]["message"] == "змінна 'z' не визначена"


def test_trace_text_on_error(sipl, source):
    code, out, err = sipl("trace", source("begin y := z end"))
    assert code == EXIT_RUNTIME
    assert out.splitlines()[-1] == "[1:12]   Failed message=\"змінна 'z' не визначена\""
    assert err == "Помилка: Рядок 1, колонка 12: змінна 'z' не визначена\n"


def test_tree_text(sipl, source):
    code, out, _ = sipl("tree", source("begin skip end"))
    assert code == EXIT_OK
    assert out.splitlines()[0] == "<program>  [1:1-1:15]"


def test_tree_json(sipl):
    code, out, _ = sipl("tree", POWER, "--json")
    data = json.loads(out)
    assert code == EXIT_OK and data["command"] == "tree"
    assert data["tree"]["symbol"] == "program"
    assert data["tree"]["children"][0] == {
        "symbol": "begin", "text": "begin", "span": {"line": 1, "column": 1, "end_line": 1, "end_column": 6},
    }


def test_tree_dot(sipl):
    code, out, _ = sipl("tree", POWER, "--format", "dot")
    assert code == EXIT_OK
    assert out.startswith("digraph parse_tree {")


def test_tree_svg_to_file(sipl, tmp_path):
    target = tmp_path / "tree.svg"
    assert sipl("tree", POWER, "--format", "svg", "-o", str(target)) == (EXIT_OK, "", "")
    assert target.read_text(encoding="utf-8").startswith("<svg ")


def test_tree_syntax_error(sipl, source):
    code, out, err = sipl("tree", source("begin end"), "-o", "never.svg")
    assert (code, out) == (EXIT_SYNTAX, "")
    assert err.startswith("Помилка: Рядок 1, колонка 7")
    assert not Path("never.svg").exists()


def test_compare_to_file(sipl, tmp_path):
    target = tmp_path / "compare.html"
    assert sipl("compare", POWER, "-o", str(target)) == (EXIT_OK, "", "")
    assert target.read_text(encoding="utf-8").count("<svg ") == 2


def test_compare_json(sipl):
    code, out, _ = sipl("compare", POWER, "--json")
    data = json.loads(out)
    assert code == EXIT_OK
    assert data["tree"]["symbol"] == "program"
    assert data["ast_tree"]["symbol"] == "Program"
    assert data["comparison"]["ast"] == {"nodes": 17, "depth": 7}


def test_missing_file(sipl):
    code, out, err = sipl("check", "no_such_file.sipl", "--json")
    assert code == EXIT_USAGE
    assert json.loads(out)["error"]["kind"] == "usage"


def test_missing_file_text(sipl):
    code, _, err = sipl("check", "no_such_file.sipl")
    assert code == EXIT_USAGE
    assert err.startswith("Помилка: не вдалося прочитати файл 'no_such_file.sipl'")


@pytest.mark.parametrize("arg, message", [
    ("X", "очікувалось ЗМІННА=ЧИСЛО, отримано 'X'"),
    ("=5", "очікувалось ЗМІННА=ЧИСЛО, отримано '=5'"),
    ("X=abc", "'abc' не є цілим числом (у 'X=abc')"),
])
def test_bad_state_argument(sipl, arg, message):
    code, _, err = sipl("run", POWER, arg)
    assert code == EXIT_USAGE
    assert err == f"Помилка: {message}\n"


def test_unknown_command():
    with pytest.raises(SystemExit) as exc:
        main(["fly", POWER])
    assert exc.value.code == EXIT_USAGE


def _subprocess(*args):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run(
        [sys.executable, "-m", "sipl", *args], capture_output=True, text=True, encoding="utf-8", env=env,
    )


def test_python_m_sipl_run():
    result = _subprocess("run", POWER, "X=2", "Y=3", "--json")
    assert result.returncode == EXIT_OK
    assert json.loads(result.stdout)["state"]["R"] == 8


def test_python_m_sipl_syntax_error(source):
    result = _subprocess("check", source("begin end"))
    assert result.returncode == EXIT_SYNTAX
    assert "Рядок 1, колонка 7" in result.stderr
