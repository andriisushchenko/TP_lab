from pathlib import Path

import pytest
from lark.exceptions import UnexpectedInput

from sipl.grammar import parser

HERE = Path(__file__).parent
VALID = sorted((HERE / "grammar" / "valid").glob("*.sipl"))
INVALID = sorted((HERE / "grammar" / "invalid").glob("*.sipl"))
EXAMPLES = sorted((HERE.parent / "examples").glob("*.sipl"))


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


@pytest.mark.parametrize("path", VALID + EXAMPLES, ids=lambda p: p.name)
def test_valid_programs_parse(path):
    tree = parser.parse(_read(path))
    assert tree.data == "program"


@pytest.mark.parametrize("path", INVALID, ids=lambda p: p.name)
def test_invalid_programs_rejected(path):
    with pytest.raises(UnexpectedInput):
        parser.parse(_read(path))


def _body(src):
    return parser.parse("begin " + src + " end").children[0]


def test_mul_binds_tighter_than_add():
    expr = _body("x := 1 + 2 * 3").children[1]
    assert expr.data == "add" and expr.children[1].data == "mul"


def test_sub_is_left_associative():
    expr = _body("x := 1 - 2 - 3").children[1]
    assert expr.data == "sub" and expr.children[0].data == "sub"


def test_not_binds_tighter_than_or():
    cond = _body("if not x = 1 or y = 2 then skip else skip").children[0]
    assert cond.data == "or_" and cond.children[0].data == "not_"


def test_while_binds_tighter_than_sequence():
    seq = _body("while x > 0 do x := x - 1; y := 1")
    assert [c.data for c in seq.children] == ["while_stmt", "assign"]


def test_error_reports_line_and_column():
    with pytest.raises(UnexpectedInput) as exc:
        parser.parse("begin\n  x := 1\n  y := 2\nend")
    assert (exc.value.line, exc.value.column) == (3, 3)
