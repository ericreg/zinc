from typing import NamedTuple
from antlr4 import *
from zinc.parser.zincLexer import zincLexer as ZincLexer
from zinc.parser.zincParser import zincParser as ZincParser
from zinc.parser.zincVisitor import zincVisitor as ZincVisitor
from pathlib import Path
from enum import Enum, auto


class Statement:
    def render(self) -> str:
        raise NotImplementedError("Subclasses must implement render()")

class VariableAssignment(Statement):
    def __init__(self, variable_name: str, value: object):
        self.variable_name = variable_name
        self.value = value

    def render(self) -> str:
        return f"let {self.variable_name} = {self.value};"


class BaseType(Enum):
    INTEGER = auto()
    STRING = auto()
    BOOLEAN = auto()
    FLOAT = auto()

    def __repr__(self):
        return self.name

def parse_literal(literal_text: str) -> BaseType:
    if literal_text.isdigit():
        return BaseType.INTEGER
    elif literal_text.replace('.', '', 1).isdigit() and literal_text.count('.') < 2:
        return BaseType.FLOAT
    elif literal_text.startswith('"') and literal_text.endswith('"'):
        return BaseType.STRING
    elif literal_text in ("true", "false"):
        return BaseType.BOOLEAN
    else:
        raise ValueError(f"Unknown literal type: {literal_text}")

class Symbol(NamedTuple):
    name: str
    type: BaseType
    value: object

    def __repr__(self):
        return f"Symbol(name={self.name}, type={self.type})"


class Scope:
    def __init__(self, parent = None):
        self.parent: Scope | None = parent
        self._symbols: dict[str, Symbol] = dict()
        self.function = None
        self.children: list[Scope] = []

    def add_symbol(self, symbol: Symbol) -> None:
        self._symbols[symbol.name] = symbol

    def lookup(self, ctx: ParserRuleContext) -> Symbol | None:
        key = ctx.getSourceInterval()
        if key in self._symbols:
            return self._symbols[key]
        elif self.parent:
            return self.parent.lookup(ctx)
        else:
            return None

    def enter_scope(self) -> 'Scope':
        child_scope = Scope(parent=self)
        self.children.append(child_scope)
        return child_scope

    def exit_scope(self) -> 'Scope':
        if self.parent is None:
            raise RuntimeError("Cannot exit the global scope")
        return self.parent
        



class Program:
    def __init__(self, scope: Scope, statements: list[Statement]):
        self.scope = scope
        self.statements = statements

    def render(self) -> str:
        """Render the program as valid Rust code."""
        rust_code = "fn main() {\n"

        # Render each statement with proper indentation
        for stmt in self.statements:
            rust_code += "    " + stmt.render() + "\n"

        rust_code += "}\n"
        return rust_code


class Visitor(ZincVisitor):

    def __init__(self) -> None:
        # key, source_location, resolved type
        # self._type_map = set()
        self._expr_map: dict[str, Symbol] = dict()
        self._scope = Scope()
        self.statements: list[Statement] = []

    def visitLiteral(self, ctx: ZincParser.LiteralContext):
        text = ctx.getText()
        source_interval = ctx.getSourceInterval()
        literal = parse_literal(text)
        sym = Symbol(name=text, type=literal, value=text)
        self._scope.add_symbol(sym)

        self._expr_map[source_interval] = sym

        print(f"literal: {sym}")
        return self.visitChildren(ctx)

    def visitProgram(self, ctx):
        print("Visiting program")
        return self.visitChildren(ctx)
    

    def visitFunctionDeclaration(self, ctx: ZincParser.FunctionDeclarationContext):
        func_name = ctx.IDENTIFIER().getText()
        print(f"Visiting function declaration: {func_name}")

        # add a new scope for the function
        self._scope = self._scope.enter_scope()

        result = super().visitFunctionDeclaration(ctx)
        self._scope = self._scope.exit_scope()
        return result
    
    def visitVariableAssignment(self, ctx):
        var_name = ctx.assignmentTarget().getText()
        value = ctx.expression().getText()

        # Create a VariableAssignment statement
        stmt = VariableAssignment(variable_name=var_name, value=value)
        self.statements.append(stmt)

        return self.visitChildren(ctx)



file_path = Path("programs/variable_assignment.zinc")
input_text = file_path.read_text()

input_stream = InputStream(input_text)
lexer = ZincLexer(input_stream)
stream = CommonTokenStream(lexer)
parser = ZincParser(stream)

tree = parser.program()

visitor = Visitor()
visitor.visit(tree)

print(tree.toStringTree(recog=parser))

# Create the Program object with the collected statements
program = Program(scope=visitor._scope, statements=visitor.statements)

# Render and print the Rust code
print("\n" + "="*50)
print("Rendered Rust Code:")
print("="*50)
print(program.render())