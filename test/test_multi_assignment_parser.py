"""Parser coverage for multi-name assignments."""

from antlr4 import CommonTokenStream, InputStream
from antlr4.error.ErrorListener import ErrorListener
from zinc.parser.zincLexer import zincLexer
from zinc.parser.zincParser import zincParser


class RecordingErrorListener(ErrorListener):
    """Collect parser errors without printing them during tests."""

    def __init__(self) -> None:
        """Initialize the recorded syntax error list."""
        self.messages: list[str] = []

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e) -> None:  # noqa: N802
        """Record one lexer or parser syntax error."""
        self.messages.append(f"{line}:{column}: {msg}")


def parse_program(source: str) -> tuple[zincParser.ProgramContext, list[str]]:
    """Parse Zinc source and collect syntax errors."""
    listener = RecordingErrorListener()
    lexer = zincLexer(InputStream(source))
    parser = zincParser(CommonTokenStream(lexer))
    lexer.removeErrorListeners()
    parser.removeErrorListeners()
    lexer.addErrorListener(listener)
    parser.addErrorListener(listener)
    tree = parser.program()
    return tree, listener.messages


def test_broadcast_and_typed_multi_assignment_parse() -> None:
    """Tuple targets parse for untyped and typed multi-name assignment."""
    tree, errors = parse_program(
        """
        fn main() {
            x, y, z = 1
            a, b, c: f32 = 1
            (single,) = (1,)
            typed_x, typed_y: f32 = (1, 2)
        }
        """
    )

    assert errors == []
    block = tree.statement(0).functionDeclaration().block()
    assert block.statement(0).variableAssignment().assignmentTarget().tupleAssignmentTarget() is not None
    typed_target = block.statement(1).typedVariableAssignment().typedAssignmentTarget()
    assert typed_target.tupleAssignmentTarget() is not None
    assert block.statement(2).variableAssignment().assignmentTarget().tupleAssignmentTarget() is not None
    typed_destructure_target = block.statement(3).typedVariableAssignment().typedAssignmentTarget()
    assert typed_destructure_target.tupleAssignmentTarget() is not None
