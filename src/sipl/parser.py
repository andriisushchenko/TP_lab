from lark import Transformer, v_args
from lark.exceptions import UnexpectedCharacters, UnexpectedToken

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
from sipl.grammar import parser as lark_parser

TOKEN_NAMES = {"NAME": "змінна", "NUMBER": "число", "$END": "кінець програми"}


class SiplSyntaxError(Exception):
    def __init__(self, message, line, column):
        super().__init__(f"Рядок {line}, колонка {column}: {message}")
        self.message = message
        self.line = line
        self.column = column


def _span(meta):
    return SourceSpan(meta.line, meta.column, meta.end_line, meta.end_column)


@v_args(meta=True)
class _ToAst(Transformer):
    def program(self, meta, c):
        return Program(c[0], span=_span(meta))

    def stmt_seq(self, meta, c):
        return Seq(c, span=_span(meta))

    def assign(self, meta, c):
        return Assign(str(c[0]), c[1], span=_span(meta))

    def if_stmt(self, meta, c):
        return If(c[0], c[1], c[2], span=_span(meta))

    def while_stmt(self, meta, c):
        return While(c[0], c[1], span=_span(meta))

    def block(self, meta, c):
        return c[0]

    def skip_stmt(self, meta, c):
        return Skip(span=_span(meta))

    def num(self, meta, c):
        return Num(int(c[0]), span=_span(meta))

    def neg_num(self, meta, c):
        return Num(-int(c[0]), span=_span(meta))

    def var(self, meta, c):
        return Var(str(c[0]), span=_span(meta))

    def add(self, meta, c):
        return BinOp("+", c[0], c[1], span=_span(meta))

    def sub(self, meta, c):
        return BinOp("-", c[0], c[1], span=_span(meta))

    def mul(self, meta, c):
        return BinOp("*", c[0], c[1], span=_span(meta))

    def div(self, meta, c):
        return BinOp("div", c[0], c[1], span=_span(meta))

    def mod(self, meta, c):
        return BinOp("mod", c[0], c[1], span=_span(meta))

    def eq(self, meta, c):
        return Compare("=", c[0], c[1], span=_span(meta))

    def gt(self, meta, c):
        return Compare(">", c[0], c[1], span=_span(meta))

    def or_(self, meta, c):
        return Or(c[0], c[1], span=_span(meta))

    def not_(self, meta, c):
        return Not(c[0], span=_span(meta))


def _token_name(name):
    if name in TOKEN_NAMES:
        return TOKEN_NAMES[name]
    return "'" + lark_parser.get_terminal(name).pattern.value + "'"


def parse(source: str) -> Program:
    try:
        tree = lark_parser.parse(source)
    except UnexpectedCharacters as e:
        raise SiplSyntaxError(f"невідомий символ '{e.char}'", e.line, e.column) from None
    except UnexpectedToken as e:
        found = "кінець програми" if e.token.type == "$END" else f"'{e.token}'"
        expected = ", ".join(sorted(_token_name(t) for t in e.accepts))
        raise SiplSyntaxError(f"неочікуване {found}; очікувалось: {expected}", e.line, e.column) from None
    return _ToAst().transform(tree)
