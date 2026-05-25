"""Parser coverage for raw backtick string literals."""

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


def test_raw_multiline_string_parses_as_one_literal() -> None:
    """Backtick raw strings can span lines and preserve doubled backticks."""
    tree, errors = parse_program(
        """
        fn main() {
            text = `line 1
line ``2
{literal}`
        }
        """
    )

    assert errors == []
    literal = (
        tree.statement(0)
        .functionDeclaration()
        .block()
        .statement(0)
        .variableAssignment()
        .expression()
        .primaryExpression()
        .literal()
    )
    assert literal.getText() == "`line 1\nline ``2\n{literal}`"


def test_raw_strings_parse_in_calls_and_struct_literals() -> None:
    """Raw strings should parse anywhere normal string expressions are valid."""
    tree, errors = parse_program(
        """
        struct Message {
            body: string
        }

        fn echo(text) {
            print(text)
        }

        fn main() {
            msg = Message {
                body: `hello
world`
            }
            echo(`tick: ```)
        }
        """
    )

    assert errors == []
    block = tree.statement(2).functionDeclaration().block()
    struct_expr = block.statement(0).variableAssignment().expression()
    call_expr = block.statement(1).expressionStatement().expression()
    assert struct_expr.primaryExpression().structInstantiation() is not None
    assert call_expr.expression().primaryExpression().IDENTIFIER().getText() == "echo"
