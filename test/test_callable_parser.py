"""Parser coverage for first-class callable syntax."""

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


def test_callable_annotations_and_fn_lambdas_parse() -> None:
    """Callable type annotations and expression lambdas parse together."""
    tree, errors = parse_program(
        """
        fn apply(f: (i64) -> i64, x: i64) {
            run = fn(value: i64) {
                return f(value)
            }
            print(run(x))
        }
        """
    )

    assert errors == []
    decl = tree.statement(0).functionDeclaration()
    assert decl.parameterList().parameter(0).typeAlternative().getText() == "(i64)->i64"
    assign_expr = decl.block().statement(0).variableAssignment().expression()
    assert isinstance(assign_expr, zincParser.LambdaExprContext)


def test_bound_method_reference_parses_in_value_position() -> None:
    """Member access can appear as a callable value without trailing call parens."""
    tree, errors = parse_program(
        """
        struct Counter {
            count: 0

            fn inc() {
                self.count = self.count + 1
            }
        }

        fn main() {
            c = Counter {}
            step = c.inc
        }
        """
    )

    assert errors == []
    assign_expr = tree.statement(1).functionDeclaration().block().statement(1).variableAssignment().expression()
    assert isinstance(assign_expr, zincParser.MemberAccessExprContext)


def test_callable_field_and_return_lambda_parse() -> None:
    """Callable field annotations and returned lambdas parse together."""
    tree, errors = parse_program(
        """
        struct Pipeline {
            transform: (i64) -> i64
        }

        fn make() {
            return fn(x: i64) {
                return x + 1
            }
        }
        """
    )

    assert errors == []
    field = tree.statement(0).structDeclaration().structBody().structMember(0).structField()
    assert field.typeAlternative().getText() == "(i64)->i64"
    return_expr = tree.statement(1).functionDeclaration().block().statement(0).returnStatement().expression()
    assert isinstance(return_expr, zincParser.LambdaExprContext)


def test_module_qualified_reference_and_returned_callable_call_parse() -> None:
    """Module-qualified references and call-on-call expressions parse correctly."""
    tree, errors = parse_program(
        """
        import modules/_lib/math as math

        fn choose(flag) {
            if flag {
                return math.add
            }
            return math.add
        }

        fn main() {
            f = math.add
            print(f(2, 3))
            print(choose(true)(2, 3))
        }
        """
    )

    assert errors == []
    assign_expr = tree.statement(2).functionDeclaration().block().statement(0).variableAssignment().expression()
    assert isinstance(assign_expr, zincParser.MemberAccessExprContext)
    print_call = tree.statement(2).functionDeclaration().block().statement(2).expressionStatement().expression()
    nested_call = print_call.argumentList().argument(0).expression()
    assert isinstance(nested_call, zincParser.FunctionCallExprContext)
    assert isinstance(nested_call.expression(), zincParser.FunctionCallExprContext)


def test_named_and_default_arguments_parse() -> None:
    """Parameter defaults and named call arguments parse without making '=' an expression."""
    tree, errors = parse_program(
        """
        fn add(x: i32 = 10, y = 20) {
            print(x + y)
        }

        fn main() {
            add(y=2, x=1)
            add(1, y=2)
            add(1, x=2)
        }
        """
    )

    assert errors == []
    params = tree.statement(0).functionDeclaration().parameterList().parameter()
    assert params[0].expression().getText() == "10"
    assert params[1].expression().getText() == "20"
    first_call = tree.statement(1).functionDeclaration().block().statement(0).expressionStatement().expression()
    assert first_call.argumentList().argument(0).IDENTIFIER().getText() == "y"
    assert first_call.argumentList().argument(1).IDENTIFIER().getText() == "x"
    duplicate_syntax_call = tree.statement(1).functionDeclaration().block().statement(2).expressionStatement().expression()
    assert duplicate_syntax_call.argumentList().argument(1).IDENTIFIER().getText() == "x"


def test_bar_lambda_syntax_is_rejected() -> None:
    """The old bar-lambda syntax is no longer accepted."""
    _, errors = parse_program(
        """
        fn main() {
            f = |x| {
                return x
            }
        }
        """
    )

    assert errors
