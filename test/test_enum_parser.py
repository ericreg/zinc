"""Parser coverage for enum declarations, construction, and match patterns."""

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


def test_enum_declaration_with_variants_and_methods_parses() -> None:
    """Enums accept unit variants, payload variants, and trailing methods."""
    tree, errors = parse_program(
        """
        enum Message {
            Quit
            Move { x: i32, y: i32 }

            fn origin() {
                return Message.Move { x: 0, y: 0 }
            }
        }
        """
    )

    assert errors == []
    enum_decl = tree.statement(0).enumDeclaration()
    assert enum_decl is not None
    assert len(enum_decl.enumBody().enumVariant()) == 2
    assert len(enum_decl.enumBody().functionDeclaration()) == 1


def test_enum_variant_construction_and_match_patterns_parse() -> None:
    """Payload construction and enum match destructuring parse together."""
    tree, errors = parse_program(
        """
        fn main() {
            msg = Message.Move { x: 1, y: 2 }
            match msg {
                Message.Quit => {
                    print("quit")
                },
                Message.Move { x, y: py } => {
                    print("{x}")
                    print("{py}")
                },
            }
        }
        """
    )

    assert errors == []
    assign_expr = tree.statement(0).functionDeclaration().block().statement(0).variableAssignment().expression()
    assert isinstance(assign_expr, zincParser.PrimaryExprContext)
    assert assign_expr.primaryExpression().enumVariantConstruction() is not None
    match_stmt = tree.statement(0).functionDeclaration().block().statement(1).matchStatement()
    assert match_stmt is not None
    assert match_stmt.matchArm(1).pattern().enumVariantPattern() is not None


def test_enum_match_requires_statement_position() -> None:
    """Match remains statement-only even with enum patterns available."""
    _, errors = parse_program(
        """
        fn main() {
            value = match msg {
                Message.Quit => 1,
            }
        }
        """
    )

    assert errors
