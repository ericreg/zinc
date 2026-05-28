"""Parser coverage for bitwise operators."""

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


def test_bitwise_expressions_and_compound_assignments_parse() -> None:
    """Bitwise expressions and assignment operators parse cleanly."""
    tree, errors = parse_program(
        """
        fn main() {
            value = 1 << 2 | 1 ^ 3 & 7
            mask = !value
            value &= 1
            value |= 2
            value ^= 3
            value <<= 1
            value >>= 2
        }
        """
    )

    assert errors == []
    block = tree.statement(0).functionDeclaration().block()
    assert isinstance(block.statement(0).variableAssignment().expression(), zincParser.BitwiseOrExprContext)
    assert block.statement(2).variableAssignment().assignmentOperator().getText() == "&="
    assert block.statement(3).variableAssignment().assignmentOperator().getText() == "|="
    assert block.statement(4).variableAssignment().assignmentOperator().getText() == "^="
    assert block.statement(5).variableAssignment().assignmentOperator().getText() == "<<="
    assert block.statement(6).variableAssignment().assignmentOperator().getText() == ">>="
