"""Parser coverage for trailing comma syntax."""

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


def test_trailing_commas_parse_in_comma_delimited_forms() -> None:
    """Trailing commas are accepted in list-like grammar positions."""
    tree, errors = parse_program(
        """
        import modules/_lib/math [ add, sub, ]

        #[type(Result<i64, string,>),]
        struct Uses [ Foo, Bar, ] {
            values: [Result<i64, string,>]
            callback: (i64, string,) -> i64
            unary_callback: (i64,) -> i64
        }

        enum Message {
            Move { x: i32, y: i32, }
        }

        fn worker(value) {
            print(value)
        }

        fn main(pair: (i64, string,), cb: (i64, string,) -> i64, unary: (i64,) -> i64,) {
            out captured,

            captured = Ok(1,)
            maybe = Some(2,)
            lambda = fn(a, b,) {
                return Ok(a + b,)
            }

            one = id(1,)
            many = mix(1, y=2, ..args,)
            spawn worker(one,)

            values = [1, 2,]
            tuple = (1, 2,)
            dict = {"a": 1, "b": 2,}
            set = {1, 2,}
            anon = struct { x: 1, y: 2, }
            named = Point { x: 1, y: 2, }
            msg = Message.Move { x: 1, y: 2, }

            match tuple {
                (x, y,) => {
                    print(x)
                },
            }

            match maybe {
                Some(value,) => {
                    print(value)
                },
                None => {
                    print("none")
                },
            }

            match msg {
                Message.Move { x, y: py, } => {
                    print(py)
                },
            }
        }
        """
    )

    assert errors == []
    assert tree.statement(0).importStatement().importNameList().IDENTIFIER(1).getText() == "sub"
    main_decl = tree.statement(4).functionDeclaration()
    assert len(main_decl.parameterList().parameter()) == 3
    assert main_decl.block().statement(1).variableAssignment().expression().primaryExpression().builtinResultOptionConstructor() is not None
    assert len(main_decl.block().statement(6).spawnStatement().argumentList().argument()) == 1
