"""Parser coverage for Zinc struct composition syntax."""

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


def test_struct_composition_parses_orthogonal_and_merge_forms() -> None:
    """Struct declarations accept both composition syntaxes."""
    tree, errors = parse_program(
        """
        struct Flat [ File | Message ] {
            id: i32
        }

        struct Override [ File, Message ] {
            id: i32
        }
        """
    )

    assert errors == []
    flat_decl = tree.statement(0).structDeclaration()
    override_decl = tree.statement(1).structDeclaration()
    assert flat_decl.structComposition().orthogonalComposition() is not None
    assert override_decl.structComposition().mergeComposition() is not None


def test_struct_composition_rejects_mixed_operators() -> None:
    """A single composition clause cannot mix `|` and `,`."""
    _, errors = parse_program(
        """
        struct Bad [ File | Message, Audit ] {
        }
        """
    )

    assert errors
