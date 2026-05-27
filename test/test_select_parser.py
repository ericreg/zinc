"""Parser coverage for Zinc select statements."""

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


def test_select_statement_parses_receive_send_and_default_cases() -> None:
    """Select accepts receive, send, and default arms as statements."""
    tree, errors = parse_program(
        """
        fn main() {
            select {
                case msg = <-messages {
                    print("{msg}")
                }
                case work <- 1 {
                    print("sent")
                }
                default {
                    print("idle")
                }
            }
        }
        """
    )

    assert errors == []
    select_stmt = tree.statement(0).functionDeclaration().block().statement(0).selectStatement()
    assert select_stmt is not None
    assert len(select_stmt.selectCase()) == 3
    assert isinstance(select_stmt.selectCase(0), zincParser.SelectReceiveCaseContext)
    assert isinstance(select_stmt.selectCase(1), zincParser.SelectSendCaseContext)
    assert isinstance(select_stmt.selectCase(2), zincParser.SelectDefaultCaseContext)


def test_select_statement_parses_no_binding_tuple_binding_and_channel_expr() -> None:
    """Select accepts close-aware receive bindings and general channel expressions."""
    tree, errors = parse_program(
        """
        fn main() {
            ctx = Context.background()
            values = chan()
            select {
                case <-ctx.done() {
                    print("done")
                }
                case value, ok = <-values {
                    print("{value}")
                    print("{ok}")
                }
            }
        }
        """
    )

    assert errors == []
    select_stmt = tree.statement(0).functionDeclaration().block().statement(2).selectStatement()
    assert select_stmt is not None
    first_case = select_stmt.selectCase(0)
    second_case = select_stmt.selectCase(1)
    assert isinstance(first_case, zincParser.SelectReceiveCaseContext)
    assert first_case.selectReceiveBinding() is None
    assert isinstance(second_case, zincParser.SelectReceiveCaseContext)
    assert second_case.selectReceiveBinding() is not None
    assert second_case.selectReceiveBinding().tupleAssignmentTarget() is not None


def test_select_cannot_appear_in_expression_position() -> None:
    """Select is a statement, not an expression."""
    _, errors = parse_program(
        """
        fn main() {
            value = select {
                default {
                    print("idle")
                }
            }
        }
        """
    )

    assert errors


def test_select_receive_requires_identifier_binder() -> None:
    """Receive cases still reject arbitrary assignment targets at parse time."""
    _, errors = parse_program(
        """
        fn main() {
            select {
                case value.item = <-messages {
                    print("nope")
                }
            }
        }
        """
    )

    assert errors
