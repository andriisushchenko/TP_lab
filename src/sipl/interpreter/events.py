import json
from dataclasses import asdict, dataclass

from sipl.ast import SourceSpan


@dataclass
class BeforeStatement:
    statement: str
    span: SourceSpan | None


@dataclass
class AfterStatement:
    statement: str
    span: SourceSpan | None


@dataclass
class VariableChanged:
    name: str
    old: int | None
    new: int
    span: SourceSpan | None


@dataclass
class ConditionChecked:
    result: bool
    span: SourceSpan | None


@dataclass
class Finished:
    state: dict[str, int]


@dataclass
class Failed:
    message: str
    span: SourceSpan | None


def to_dict(event):
    return {"event": type(event).__name__, **asdict(event)}


def to_json(events):
    return json.dumps([to_dict(e) for e in events], ensure_ascii=False, indent=2)
