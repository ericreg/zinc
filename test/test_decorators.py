"""Parser coverage for declaration decorators."""

from antlr4 import CommonTokenStream, InputStream
from antlr4.error.ErrorListener import ErrorListener
from zinc.parser.zincLexer import zincLexer
from zinc.parser.zincParser import zincParser


class RecordingErrorListener(ErrorListener):
    """Collect parser errors without printing them during tests."""

    def __init__(self) -> None:
        """Initialize an empty error list."""
        self.messages: list[str] = []

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e) -> None:  # noqa: N802
        """Record one parser syntax error."""
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


def test_decorator_syntax_parses() -> None:
    """Function decorators support direct, factory, qualified, stacked, and post-constraint forms."""
    tree, errors = parse_program(
        """
        #[x in [i64]]
        @empty()
        @pkg.trace("score")
        @identity
        fn score(x: i64) -> i64 {
            return x
        }
        """
    )

    assert errors == []
    decl = tree.statement(0).functionDeclaration()
    assert decl.attributeBlock(0).getText() == "#[xin[i64]]"
    assert [decorator.qualifiedName().getText() for decorator in decl.decorator()] == ["empty", "pkg.trace", "identity"]
    assert decl.decorator(0).argumentList() is None
    assert decl.decorator(1).argumentList().getText() == '"score"'
    assert decl.decorator(2).argumentList() is None


def test_decorators_parse_on_later_targets() -> None:
    """Structs, enums, and methods parse decorators even though V1 rejects them semantically."""
    tree, errors = parse_program(
        """
        @model
        struct Box {
            value: i64

            @method_dec()
            fn read() {
                return self.value
            }
        }

        #[type(Tone) in [Tone]]
        @enum_dec
        enum Tone {
            High
            Low
        }
        """
    )

    assert errors == []
    struct_decl = tree.statement(0).structDeclaration()
    enum_decl = tree.statement(1).enumDeclaration()
    assert struct_decl.decorator(0).qualifiedName().getText() == "model"
    assert struct_decl.structBody().structMember(1).functionDeclaration().decorator(0).qualifiedName().getText() == "method_dec"
    assert enum_decl.attributeBlock(0).getText() == "#[type(Tone)in[Tone]]"
    assert enum_decl.decorator(0).qualifiedName().getText() == "enum_dec"


def test_invalid_decorator_placement_fails_to_parse() -> None:
    """Decorators are declaration syntax, not expression syntax."""
    _tree, errors = parse_program(
        """
        fn main() {
            value = @trace 1
        }
        """
    )

    assert errors
