import json
from pathlib import Path

import pytest

from sipl.ast import SourceSpan
from sipl.interpreter import SiplRuntimeError, run, trace
from sipl.interpreter.events import (
    AfterStatement,
    BeforeStatement,
    ConditionChecked,
    Failed,
    Finished,
    VariableChanged,
    to_json,
)
from sipl.parser import parse

EXAMPLES = Path(__file__).parent.parent / "examples"


def _trace(src, state=None, **kwargs):
    return trace(parse("begin " + src + " end"), state, **kwargs)


def _names(events):
    return [type(e).__name__ for e in events]


def test_assign_events():
    events = _trace("x := 1")
    span = SourceSpan(1, 7, 1, 13)
    assert events == [
        BeforeStatement("Assign", span),
        VariableChanged("x", None, 1, span),
        AfterStatement("Assign", span),
        Finished({"x": 1}),
    ]


def test_old_value_in_variable_changed():
    changes = [e for e in _trace("x := 1; x := x + 5") if isinstance(e, VariableChanged)]
    assert [(e.old, e.new) for e in changes] == [(None, 1), (1, 6)]


def test_sequence_has_no_own_events():
    assert _names(_trace("skip; skip")) == [
        "BeforeStatement", "AfterStatement",
        "BeforeStatement", "AfterStatement",
        "Finished",
    ]


def test_if_events():
    events = _trace("if x > 0 then y := 1 else y := 2", {"x": 0})
    assert _names(events) == [
        "BeforeStatement",
        "ConditionChecked",
        "BeforeStatement", "VariableChanged", "AfterStatement",
        "AfterStatement",
        "Finished",
    ]
    assert events[1] == ConditionChecked(False, SourceSpan(1, 10, 1, 15))
    assert events[3].new == 2


def test_while_checks_condition_each_iteration():
    events = _trace("while x > 0 do x := x - 1", {"x": 3})
    checks = [e.result for e in events if isinstance(e, ConditionChecked)]
    assert checks == [True, True, True, False]


def test_finished_state_equals_run():
    program = parse((EXAMPLES / "power.sipl").read_text(encoding="utf-8"))
    events = trace(program, {"X": 2, "Y": 5})
    assert events[-1] == Finished(run(program, {"X": 2, "Y": 5}))


def test_error_ends_with_failed():
    events = _trace("x := 1; y := z")
    assert _names(events)[-1] == "Failed"
    assert events[-1] == Failed("змінна 'z' не визначена", SourceSpan(1, 20, 1, 21))
    assert VariableChanged("x", None, 1, SourceSpan(1, 7, 1, 13)) in events


def test_step_limit_ends_with_failed():
    events = _trace("while 1 = 1 do skip", max_iterations=3)
    assert isinstance(events[-1], Failed)
    assert _names(events).count("ConditionChecked") == 4


def test_run_with_listener_gets_same_events():
    program = parse("begin x := 2; if x > 1 then x := 0 else skip end")
    received = []
    run(program, on_event=received.append)
    assert received == trace(program)


def test_run_still_raises_with_listener():
    received = []
    with pytest.raises(SiplRuntimeError):
        run(parse("begin x := y end"), on_event=received.append)
    assert isinstance(received[-1], Failed)


def test_json():
    data = json.loads(to_json(_trace("x := 1")))
    assert data[0] == {
        "event": "BeforeStatement",
        "statement": "Assign",
        "span": {"line": 1, "column": 7, "end_line": 1, "end_column": 13},
    }
    assert data[1] == {
        "event": "VariableChanged",
        "name": "x",
        "old": None,
        "new": 1,
        "span": {"line": 1, "column": 7, "end_line": 1, "end_column": 13},
    }
    assert data[-1] == {"event": "Finished", "state": {"x": 1}}
