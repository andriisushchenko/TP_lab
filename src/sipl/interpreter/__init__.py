import operator

from sipl.ast import Assign, BinOp, Compare, If, Not, Num, Or, Seq, Skip, Var, While
from sipl.interpreter.events import (
    AfterStatement,
    BeforeStatement,
    ConditionChecked,
    Failed,
    Finished,
    VariableChanged,
)

MAX_ITERATIONS = 100_000

ARITH = {
    "+": operator.add,
    "-": operator.sub,
    "*": operator.mul,
    "div": operator.floordiv,
    "mod": operator.mod,
}

COMPARE = {
    "=": operator.eq,
    ">": operator.gt,
}


class SiplRuntimeError(Exception):
    def __init__(self, message, span=None):
        if span is None:
            super().__init__(message)
        else:
            super().__init__(f"Рядок {span.line}, колонка {span.column}: {message}")
        self.message = message
        self.span = span


class StepLimitExceeded(SiplRuntimeError):
    pass


def eval_a(node, state):
    if isinstance(node, Num):
        return node.value
    if isinstance(node, Var):
        if node.name not in state:
            raise SiplRuntimeError(f"змінна '{node.name}' не визначена", node.span)
        return state[node.name]
    if isinstance(node, BinOp):
        left = eval_a(node.left, state)
        right = eval_a(node.right, state)
        if node.op in ("div", "mod") and right == 0:
            raise SiplRuntimeError(f"ділення на нуль ({node.op})", node.span)
        return ARITH[node.op](left, right)
    raise TypeError(f"не арифметичний вираз: {node}")


def eval_b(node, state):
    if isinstance(node, Compare):
        return COMPARE[node.op](eval_a(node.left, state), eval_a(node.right, state))
    if isinstance(node, Or):
        return eval_b(node.left, state) or eval_b(node.right, state)
    if isinstance(node, Not):
        return not eval_b(node.operand, state)
    raise TypeError(f"не умова: {node}")


class Interpreter:
    def __init__(self, state, max_iterations=MAX_ITERATIONS, on_event=None):
        self.state = state
        self.max_iterations = max_iterations
        self.iterations = 0
        self.on_event = on_event

    def emit(self, event):
        if self.on_event is not None:
            self.on_event(event)

    def check(self, cond):
        result = eval_b(cond, self.state)
        self.emit(ConditionChecked(result, cond.span))
        return result

    def count_iteration(self, node):
        self.iterations += 1
        if self.max_iterations is not None and self.iterations > self.max_iterations:
            raise StepLimitExceeded(
                f"перевищено ліміт у {self.max_iterations} ітерацій циклу (можливо, нескінченний цикл)",
                node.span,
            )

    def execute(self, node):
        if isinstance(node, Seq):
            for statement in node.statements:
                self.execute(statement)
            return

        name = type(node).__name__
        self.emit(BeforeStatement(name, node.span))
        if isinstance(node, Assign):
            old = self.state.get(node.name)
            new = eval_a(node.expr, self.state)
            self.state[node.name] = new
            self.emit(VariableChanged(node.name, old, new, node.span))
        elif isinstance(node, If):
            if self.check(node.cond):
                self.execute(node.then_branch)
            else:
                self.execute(node.else_branch)
        elif isinstance(node, While):
            while self.check(node.cond):
                self.count_iteration(node)
                self.execute(node.body)
        elif isinstance(node, Skip):
            pass
        else:
            raise TypeError(f"не оператор: {node}")
        self.emit(AfterStatement(name, node.span))


def run(program, state=None, max_iterations=MAX_ITERATIONS, on_event=None):
    interpreter = Interpreter(dict(state or {}), max_iterations, on_event)
    try:
        interpreter.execute(program.body)
    except SiplRuntimeError as e:
        interpreter.emit(Failed(e.message, e.span))
        raise
    interpreter.emit(Finished(dict(interpreter.state)))
    return interpreter.state


def trace(program, state=None, max_iterations=MAX_ITERATIONS):
    events = []
    try:
        run(program, state, max_iterations, events.append)
    except SiplRuntimeError:
        pass
    return events
