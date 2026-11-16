from pathlib import Path

import pytest

from sipl.ast import Num, Program, SourceSpan
from sipl.interpreter import SiplRuntimeError, StepLimitExceeded, eval_a, eval_b, run
from sipl.parser import parse

EXAMPLES = Path(__file__).parent.parent / "examples"


def _run_file(name, state):
    return run(parse((EXAMPLES / name).read_text(encoding="utf-8")), state)


def _run(src, state=None, **kwargs):
    return run(parse("begin " + src + " end"), state, **kwargs)


def _a(src, state=None):
    return eval_a(parse("begin r := " + src + " end").body.expr, state or {})


def _b(src, state=None):
    return eval_b(parse("begin if " + src + " then skip else skip end").body.cond, state or {})


@pytest.mark.parametrize("x, y, r", [(2, 10, 1024), (3, 1, 3), (5, 3, 125), (7, 0, 1)])
def test_power(x, y, r):
    assert _run_file("power.sipl", {"X": x, "Y": y})["R"] == r


@pytest.mark.parametrize("n, f", [(0, 1), (1, 1), (5, 120), (10, 3628800)])
def test_factorial(n, f):
    assert _run_file("factorial.sipl", {"N": n})["F"] == f


@pytest.mark.parametrize("a, b, g", [(12, 18, 6), (7, 7, 7), (17, 5, 1), (100, 75, 25)])
def test_gcd(a, b, g):
    assert _run_file("gcd.sipl", {"A": a, "B": b})["A"] == g


@pytest.mark.parametrize("src, value", [
    ("42", 42),
    ("-3", -3),
    ("x", 10),
    ("x + 2", 12),
    ("x - -2", 12),
    ("x * 3", 30),
    ("x div 3", 3),
    ("x mod 3", 1),
    ("1 + 2 * 3", 7),
    ("(1 + 2) * 3", 9),
    ("10 - 4 - 3", 3),
    ("-7 div 2", -4),
    ("-7 mod 2", 1),
])
def test_arithmetic(src, value):
    assert _a(src, {"x": 10}) == value


@pytest.mark.parametrize("src, value", [
    ("1 = 1", True),
    ("1 = 2", False),
    ("2 > 1", True),
    ("1 > 2", False),
    ("1 > 1", False),
    ("1 = 2 or 2 = 2", True),
    ("1 = 2 or 2 = 3", False),
    ("not 1 = 1", False),
    ("not 1 = 2", True),
    ("not (1 = 2 or 2 = 2)", False),
])
def test_conditions(src, value):
    assert _b(src) is value


def test_assign_and_sequence():
    assert _run("x := 1; y := x + 1; x := y * 10") == {"x": 20, "y": 2}


def test_if_branches():
    assert _run("if x > 0 then y := 1 else y := 2", {"x": 5})["y"] == 1
    assert _run("if x > 0 then y := 1 else y := 2", {"x": 0})["y"] == 2


def test_while_false_never_runs():
    assert _run("while 1 > 2 do x := 1") == {}


def test_skip_keeps_state():
    assert _run("skip", {"x": 3}) == {"x": 3}


def test_nested_blocks():
    assert _run("begin x := 1; begin y := 2 end end") == {"x": 1, "y": 2}


def test_input_state_not_changed():
    state = {"x": 1}
    _run("x := 2", state)
    assert state == {"x": 1}


def test_undefined_variable():
    with pytest.raises(SiplRuntimeError) as exc:
        _run("x := y + 1")
    assert exc.value.message == "змінна 'y' не визначена"
    assert exc.value.span == SourceSpan(1, 12, 1, 13)
    assert str(exc.value) == "Рядок 1, колонка 12: змінна 'y' не визначена"


@pytest.mark.parametrize("op", ["div", "mod"])
def test_division_by_zero(op):
    with pytest.raises(SiplRuntimeError) as exc:
        _run(f"x := 1 {op} 0")
    assert exc.value.message == f"ділення на нуль ({op})"


def test_infinite_loop_stops():
    with pytest.raises(StepLimitExceeded) as exc:
        _run("while 1 = 1 do skip", max_iterations=50)
    assert "ліміт у 50 ітерацій циклу" in exc.value.message


def test_long_loop_within_limit():
    assert _run("i := 0; while 1000 > i do i := i + 1")["i"] == 1000


def test_error_without_span():
    assert str(SiplRuntimeError("помилка")) == "помилка"


def test_unknown_nodes():
    with pytest.raises(TypeError):
        eval_a(object(), {})
    with pytest.raises(TypeError):
        eval_b(object(), {})
    with pytest.raises(TypeError):
        run(Program(Num(1)))
