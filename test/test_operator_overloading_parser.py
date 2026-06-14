"""Parser coverage for operator overloading syntax."""

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


def test_operator_method_declarations_parse() -> None:
    """Struct methods parse the supported symbolic operator declaration forms."""
    tree, errors = parse_program(
        """
        struct Point {
            x: i64

            fn operator+(rhs) -> Self { return self }
            fn operator[](idx: i64) -> i64 { return idx }
            fn operator|(left, right) -> Self { return left }
            fn operator~() -> Self { return self }
            fn operator&&(rhs) -> bool { return true }
            fn operator||(rhs) -> bool { return true }
        }

        fn main() {
        }
        """
    )

    assert errors == []
    members = tree.statement(0).structDeclaration().structBody().structMember()
    names = [member.functionDeclaration().functionName().getText() for member in members if member.functionDeclaration()]
    assert names == ["operator+", "operator[]", "operator|", "operator~", "operator&&", "operator||"]


def test_custom_operator_expression_parses_at_fixed_precedence() -> None:
    """Custom infix operators parse as their own expression context."""
    tree, errors = parse_program(
        """
        fn main() {
            value = left $$ right
            mixed = a | b $$ c .. d
        }
        """
    )

    assert errors == []
    block = tree.statement(0).functionDeclaration().block()
    assert isinstance(block.statement(0).variableAssignment().expression(), zincParser.CustomOperatorExprContext)
    mixed = block.statement(1).variableAssignment().expression()
    assert isinstance(mixed, zincParser.RangeExprContext)
    assert isinstance(mixed.expression(0), zincParser.CustomOperatorExprContext)


def test_pipe_operator_expression_parses_as_bitwise_or() -> None:
    """Plain pipe operator expressions parse through the bitwise-or context."""
    tree, errors = parse_program(
        """
        fn main() {
            piped = left | right
        }
        """
    )

    assert errors == []
    block = tree.statement(0).functionDeclaration().block()
    assert isinstance(block.statement(0).variableAssignment().expression(), zincParser.BitwiseOrExprContext)


def test_compound_operator_declaration_is_rejected() -> None:
    """Compound assignment operators are not operator declaration names."""
    _tree, errors = parse_program(
        """
        struct Point {
            x: i64

            fn operator+=(rhs) -> Self { return self }
        }

        fn main() {
        }
        """
    )

    assert errors
