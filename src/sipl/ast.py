from dataclasses import asdict, dataclass, field, fields


@dataclass(frozen=True)
class SourceSpan:
    line: int
    column: int
    end_line: int
    end_column: int


@dataclass
class Node:
    span: SourceSpan | None = field(default=None, compare=False, repr=False, kw_only=True)


@dataclass
class Num(Node):
    value: int


@dataclass
class Var(Node):
    name: str


@dataclass
class BinOp(Node):
    op: str
    left: Node
    right: Node


@dataclass
class Compare(Node):
    op: str
    left: Node
    right: Node


@dataclass
class Or(Node):
    left: Node
    right: Node


@dataclass
class Not(Node):
    operand: Node


@dataclass
class Assign(Node):
    name: str
    expr: Node


@dataclass
class Seq(Node):
    statements: list[Node]


@dataclass
class If(Node):
    cond: Node
    then_branch: Node
    else_branch: Node


@dataclass
class While(Node):
    cond: Node
    body: Node


@dataclass
class Skip(Node):
    pass


@dataclass
class Program(Node):
    body: Node


def to_dict(value):
    if isinstance(value, Node):
        result = {"type": type(value).__name__}
        for f in fields(value):
            result[f.name] = to_dict(getattr(value, f.name))
        return result
    if isinstance(value, list):
        return [to_dict(item) for item in value]
    if isinstance(value, SourceSpan):
        return asdict(value)
    return value
