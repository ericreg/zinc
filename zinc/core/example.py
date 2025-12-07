from typing import NamedTuple
from antlr4 import *
from zinc.parser.zincLexer import zincLexer as ZincLexer
from zinc.parser.zincParser import zincParser as ZincParser
from zinc.parser.zincVisitor import zincVisitor as ZincVisitor
from pathlib import Path
from enum import Enum, auto


class Statement:
    pass

class VariableAssignment(Statement):
    def __init__(self, variable_name: str, value: object):
        self.variable_name = variable_name
        self.value = value




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

        return "\n".join(str(stmt) for stmt in self.statements)


class Visitor(ZincVisitor):

    def __init__(self) -> None:
        # key, source_location, resolved type
        # self._type_map = set()
        self._expr_map: dict[str, Symbol] = dict()
        self._scope = Scope()

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



# from ..core.parser.zincLexer import zincLexer
# from ..core.parser.zincParser import zincParser


# input_text = input("> ")
# lexer = HelloLexer(InputStream(input_text))
# stream = CommonTokenStream(lexer)
# parser = HelloParser(stream)

# tree = parser.r()

# print(tree.toStringTree(recog=parser))