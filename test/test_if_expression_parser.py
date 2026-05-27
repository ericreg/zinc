"""Parser coverage for Rust-style if expressions."""

from antlr4 import CommonTokenStream, InputStream
from antlr4.error.ErrorListener import ErrorListener
from zinc.parser.zincLexer import zincLexer
from zinc.parser.zincParser import zincParser


class RecordingErrorListener(ErrorListener):
    """Collect parser errors without printing them during tests."""

    def __init__(self) -> None:
        self.messages: list[str] = []

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e) -> None:  # noqa: N802
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


def test_if_expression_parses_in_assignment_argument_and_return_position() -> None:
    """If expressions parse anywhere a value expression is expected."""
    tree, errors = parse_program(
        """
        fn label(flag) {
            value = if flag {
                "enabled"
            } else {
                "disabled"
            }
            print(if flag {
                "yes"
            } else {
                "no"
            })
            return if flag {
                1
            } else {
                0
            }
        }
        """
    )

    assert errors == []
    block = tree.statement(0).functionDeclaration().block()
    assign_expr = block.statement(0).variableAssignment().expression()
    arg_expr = block.statement(1).expressionStatement().expression().argumentList().expression(0)
    return_expr = block.statement(2).returnStatement().expression()
    assert isinstance(assign_expr, zincParser.IfExprContext)
    assert isinstance(arg_expr, zincParser.IfExprContext)
    assert isinstance(return_expr, zincParser.IfExprContext)


def test_if_expression_parses_else_if_chains() -> None:
    """Else-if chains stay in expression form instead of falling back to statements."""
    tree, errors = parse_program(
        """
        fn main() {
            grade = if score >= 90 {
                "A"
            } else if score >= 80 {
                "B"
            } else {
                "C"
            }
        }
        """
    )

    assert errors == []
    assign_expr = tree.statement(0).functionDeclaration().block().statement(0).variableAssignment().expression()
    inner_if = assign_expr.ifExpression().ifExpression()
    assert inner_if is not None
    assert len(inner_if.block()) == 2


def test_if_expression_parses_without_else_for_unit_cases() -> None:
    """Expression-form if still parses when the else branch is omitted."""
    tree, errors = parse_program(
        """
        fn main() {
            result = if debug {
                print("debug")
            }
        }
        """
    )

    assert errors == []
    assign_expr = tree.statement(0).functionDeclaration().block().statement(0).variableAssignment().expression()
    if_expr = assign_expr.ifExpression()
    assert if_expr is not None
    assert if_expr.ELSE() is None
    assert len(if_expr.block()) == 1
