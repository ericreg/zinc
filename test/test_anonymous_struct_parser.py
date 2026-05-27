"""Parser coverage for anonymous struct syntax."""

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


def test_anonymous_struct_literals_and_types_parse() -> None:
    """Anonymous struct literals and parameter annotations parse together."""
    tree, errors = parse_program(
        """
        struct Holder {
            point: struct {
                x: i64
                y: i64
            }
        }

        fn area(rect: struct {
            width: i64
            height: i64
        }) {
            point = struct {
                x: 3
                y: 4
            }
            print(point.x)
            return rect.width * rect.height
        }
        """
    )

    assert errors == []
    holder_field = tree.statement(0).structDeclaration().structBody().structMember(0).structField()
    assert holder_field.type_().anonymousStructType() is not None
    area_decl = tree.statement(1).functionDeclaration()
    assert area_decl.parameterList().parameter(0).type_().anonymousStructType() is not None
    assign_expr = area_decl.block().statement(0).variableAssignment().expression()
    assert isinstance(assign_expr, zincParser.PrimaryExprContext)
    assert assign_expr.primaryExpression().anonymousStructLiteral() is not None


def test_empty_anonymous_struct_parses() -> None:
    """Empty anonymous struct literals and annotations are valid syntax."""
    tree, errors = parse_program(
        """
        fn nop(value: struct {}) {
        }

        fn main() {
            empty = struct {}
        }
        """
    )

    assert errors == []
    assert tree.statement(0).functionDeclaration().parameterList().parameter(0).type_().anonymousStructType() is not None
    assign_expr = tree.statement(1).functionDeclaration().block().statement(0).variableAssignment().expression()
    assert assign_expr.primaryExpression().anonymousStructLiteral() is not None


def test_nested_anonymous_struct_literals_parse() -> None:
    """Anonymous struct literals can nest inside other anonymous struct fields."""
    tree, errors = parse_program(
        """
        fn main() {
            payload = struct {
                meta: struct {
                    id: 1
                }
                label: "ready"
            }
        }
        """
    )

    assert errors == []
    assign_expr = tree.statement(0).functionDeclaration().block().statement(0).variableAssignment().expression()
    outer_literal = assign_expr.primaryExpression().anonymousStructLiteral()
    nested_expr = outer_literal.fieldInit(0).expression()
    assert outer_literal is not None
    assert nested_expr.primaryExpression().anonymousStructLiteral() is not None


def test_anonymous_struct_literals_accept_optional_commas() -> None:
    """Literals support commas and trailing commas without colliding with type syntax."""
    tree, errors = parse_program(
        """
        fn main() {
            payload = struct {
                id: 1,
                meta: struct {
                    active: true,
                },
            }
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
        .anonymousStructLiteral()
    )
    assert literal is not None
    assert len(literal.fieldInit()) == 2


def test_anonymous_struct_nested_in_array_and_callable_annotations_parse() -> None:
    """Anonymous struct syntax nests inside richer type annotations."""
    tree, errors = parse_program(
        """
        struct Holder {
            points: [struct {
                x: i64
                y: i64
            }]
            transform: (struct {
                x: i64
            }) -> struct {
                label: string
            }
        }
        """
    )

    assert errors == []
    fields = tree.statement(0).structDeclaration().structBody().structMember()
    assert fields[0].structField().type_().getText() == "[struct{x:i64y:i64}]"
    assert fields[1].structField().type_().getText() == "(struct{x:i64})->struct{label:string}"


def test_anonymous_struct_type_rejects_comma_separated_fields() -> None:
    """Type-position anonymous structs stay distinct from comma-friendly literals."""
    _, errors = parse_program(
        """
        fn render(point: struct {
            x: i64,
            y: i64
        }) {
        }
        """
    )

    assert errors


def test_anonymous_struct_literals_remain_distinct_from_collection_literals() -> None:
    """`struct {}` syntax should not be confused with bare collection literals."""
    tree, errors = parse_program(
        """
        fn main() {
            anon = struct { x: 1 }
            empty_anon = struct {}
            set_like = { 1, 2 }
            empty_collection = {}
        }
        """
    )

    assert errors == []
    block = tree.statement(0).functionDeclaration().block()
    anon_expr = block.statement(0).variableAssignment().expression()
    empty_anon_expr = block.statement(1).variableAssignment().expression()
    set_expr = block.statement(2).variableAssignment().expression()
    empty_collection_expr = block.statement(3).variableAssignment().expression()
    assert anon_expr.primaryExpression().anonymousStructLiteral() is not None
    assert empty_anon_expr.primaryExpression().anonymousStructLiteral() is not None
    assert set_expr.primaryExpression().collectionLiteral() is not None
    assert empty_collection_expr.primaryExpression().collectionLiteral() is not None
