"""Parser coverage for lexical closure syntax."""

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


def test_closure_reads_super_assignment_and_nested_functions_parse() -> None:
    """Closures can read outers, use <<-, and declare nested functions."""
    tree, errors = parse_program(
        """
        fn main() {
            x = 1

            fn add(y) {
                return x + y
            }

            f = fn() {
                x <<- x + 1
                return add(x)
            }
        }
        """
    )

    assert errors == []
    main_block = tree.statement(0).functionDeclaration().block()
    nested_decl = main_block.statement(1).functionDeclaration()
    lambda_block = main_block.statement(2).variableAssignment().expression().lambdaExpression().block()
    assert nested_decl.IDENTIFIER().getText() == "add"
    assert lambda_block.statement(0).superAssignment().IDENTIFIER().getText() == "x"


def test_nested_async_function_and_await_parse() -> None:
    """Nested async declarations parse alongside direct await calls."""
    tree, errors = parse_program(
        """
        fn main() {
            base = 2
            async inner(x) {
                return base + x
            }
            await inner(3)
        }
        """
    )

    assert errors == []
    main_block = tree.statement(0).functionDeclaration().block()
    assert main_block.statement(1).asyncFunctionDeclaration().IDENTIFIER().getText() == "inner"
    await_expr = main_block.statement(2).expressionStatement().expression()
    assert isinstance(await_expr, zincParser.AwaitExprContext)


def test_super_assignment_requires_bare_identifier_target() -> None:
    """Member/index targets are not valid <<- syntax."""
    _, errors = parse_program(
        """
        fn main() {
            values = [1]
            f = fn() {
                values[0] <<- 2
            }
        }
        """
    )

    assert errors
