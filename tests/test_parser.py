from pathlib import Path

import pytest

from sipl.ast import (
    Assign,
    BinOp,
    Compare,
    If,
    Not,
    Num,
    Or,
    Program,
    Seq,
    Skip,
    SourceSpan,
    Var,
    While,
)
from sipl.parser import SiplSyntaxError, parse

HERE = Path(__file__).parent
VALID = sorted((HERE / "grammar" / "valid").glob("*.sipl"))
INVALID = sorted((HERE / "grammar" / "invalid").glob("*.sipl"))


def _body(src):
    return parse("begin " + src + " end").body


def test_power_example():
    source = (HERE.parent / "examples" / "power.sipl").read_text(encoding="utf-8")
    assert parse(source) == Program(Seq([
        Assign("R", Num(1)),
        While(
            Compare(">", Var("Y"), Num(0)),
            Seq([
                Assign("R", BinOp("*", Var("R"), Var("X"))),
                Assign("Y", BinOp("-", Var("Y"), Num(1))),
            ]),
        ),
    ]))


def test_all_statements():
    assert _body("skip; if not x = 1 or x > -2 then y := x div 2 else y := x mod 2") == Seq([
        Skip(),
        If(
            Or(Not(Compare("=", Var("x"), Num(1))), Compare(">", Var("x"), Num(-2))),
            Assign("y", BinOp("div", Var("x"), Num(2))),
            Assign("y", BinOp("mod", Var("x"), Num(2))),
        ),
    ])


def test_precedence():
    assert _body("x := 1 + 2 * (3 - 4)") == Assign(
        "x", BinOp("+", Num(1), BinOp("*", Num(2), BinOp("-", Num(3), Num(4))))
    )


def test_block_is_not_a_node():
    assert _body("begin begin skip end end") == Skip()


def test_spans():
    assign = parse("begin\n  x := -5\nend").body
    assert assign.span == SourceSpan(2, 3, 2, 10)
    assert assign.expr.span == SourceSpan(2, 8, 2, 10)


@pytest.mark.parametrize("path", VALID, ids=lambda p: p.name)
def test_valid_files_give_program(path):
    assert isinstance(parse(path.read_text(encoding="utf-8")), Program)


@pytest.mark.parametrize("path", INVALID, ids=lambda p: p.name)
def test_invalid_files_give_syntax_error(path):
    with pytest.raises(SiplSyntaxError):
        parse(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("source, line, column, message", [
    ("begin\n  x := 1\n  y := 2\nend", 3, 3, "неочікуване 'y'; очікувалось: '*', '+', '-', ';', 'div', 'end', 'mod'"),
    ("begin x = 1 end", 1, 9, "неочікуване '='; очікувалось: ':='"),
    ("begin if x > 1 then skip end", 1, 26, "неочікуване 'end'; очікувалось: 'else'"),
    ("begin x := 1 < 2 end", 1, 14, "невідомий символ '<'"),
    ("begin x := 1 end end", 1, 18, "неочікуване 'end'; очікувалось: кінець програми"),
    ("", 1, 1, "неочікуване кінець програми; очікувалось: 'begin'"),
])
def test_error_messages(source, line, column, message):
    with pytest.raises(SiplSyntaxError) as exc:
        parse(source)
    assert (exc.value.line, exc.value.column, exc.value.message) == (line, column, message)
