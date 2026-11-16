import re
from pathlib import Path

from lark import Lark

GRAMMAR = (Path(__file__).parent / "sipl.lark").read_text(encoding="utf-8")

parser = Lark(GRAMMAR, parser="lalr", lexer="basic", propagate_positions=True)

tree_parser = Lark(
    re.sub(r"^\?|\s*->\s*\w+", "", GRAMMAR, flags=re.M),
    start="program", parser="lalr", lexer="basic", propagate_positions=True, keep_all_tokens=True,
)
