from typing import NamedTuple
from antlr4 import *
from zinc.parser.zincLexer import zincLexer as ZincLexer
from zinc.parser.zincParser import zincParser as ZincParser
from zinc.parser.zincVisitor import zincVisitor as ZincVisitor
from pathlib import Path
from enum import Enum, auto
import re

INDENT = "    "

class Statement:
    def render(self) -> str:
        raise NotImplementedError("Subclasses must implement render()")

class VariableAssignment(Statement):
    def __init__(self, variable_name: str, value: object):
        self.variable_name = variable_name
        self.value = value

    def render(self) -> str:
        return f"let {self.variable_name} = {self.value};"


class PrintStatement(Statement):
    def __init__(self, arguments: list[str]):
        self.arguments = arguments

    def render(self) -> str:
        if not self.arguments:
            return "println!();"

        # Handle f-string style formatting
        # Assume the first argument is a string literal with {} placeholders
        format_string = self.arguments[0]

        # Remove surrounding quotes if present
        if format_string.startswith('"') and format_string.endswith('"'):
            format_string = format_string[1:-1]
        elif format_string.startswith("'") and format_string.endswith("'"):
            format_string = format_string[1:-1]

        # Extract variable names from {var} patterns
        variables = re.findall(r'\{(\w+)\}', format_string)

        # If there are variables, render as println! with format args
        if variables:
            # Replace {var} with {} for Rust's println! macro
            rust_format_string = re.sub(r'\{\w+\}', '{}', format_string)
            args_str = f'"{rust_format_string}"'
            # Add the variables as additional arguments
            for var in variables:
                args_str += f", {var}"
            return f"println!({args_str});"
        else:
            # No variables, just a plain string
            return f'println!("{format_string}");'


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
        rust_statements = [ INDENT + x.render() for x in self.statements ]
        rust_code += "\n".join(rust_statements) + "\n"
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

    def visitFunctionCallExpr(self, ctx: ZincParser.FunctionCallExprContext):
        # Get the function name
        func_name = ctx.expression().getText()

        # Get the arguments
        arguments = []
        if ctx.argumentList():
            for arg_expr in ctx.argumentList().expression():
                arguments.append(arg_expr.getText())

        # If this is a print() call, create a PrintStatement
        if func_name == "print":
            stmt = PrintStatement(arguments=arguments)
            self.statements.append(stmt)

        return self.visitChildren(ctx)



