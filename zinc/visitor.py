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


class AssignmentKind(Enum):
    DECLARATION = auto()      # First assignment: let mut x = ...
    REASSIGNMENT = auto()     # Same type reassignment: x = ...
    SHADOW = auto()           # Type change: let mut x = ...


class VariableAssignment(Statement):
    def __init__(self, variable_name: str, value: object, kind: AssignmentKind, needs_mut: bool = False):
        self.variable_name = variable_name
        self.value = value
        self.kind = kind
        self.needs_mut = needs_mut

    def render(self) -> str:
        if self.kind == AssignmentKind.REASSIGNMENT:
            return f"{self.variable_name} = {self.value};"
        else:
            # DECLARATION or SHADOW - both need 'let', with optional 'mut'
            mut = "mut " if self.needs_mut else ""
            return f"let {mut}{self.variable_name} = {self.value};"


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
        variables = re.findall(r"\{(\w+)\}", format_string)

        # If there are variables, render as println! with format args
        if variables:
            # Replace {var} with {} for Rust's println! macro
            rust_format_string = re.sub(r"\{\w+\}", "{}", format_string)
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
    elif literal_text.replace(".", "", 1).isdigit() and literal_text.count(".") < 2:
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


class RawAssignment(NamedTuple):
    """Raw assignment info collected during Pass 1."""
    var_name: str
    value: str
    value_type: BaseType
    index: int  # Position in statement list (for tracking order)


class Scope:
    def __init__(self, parent=None):
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

    def enter_scope(self) -> "Scope":
        child_scope = Scope(parent=self)
        self.children.append(child_scope)
        return child_scope

    def exit_scope(self) -> "Scope":
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
        rust_statements = [INDENT + x.render() for x in self.statements]
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
        # Pass 1: Collect raw assignments before processing
        self._pending_assignments: list[RawAssignment] = []
        # Track non-assignment statements with their indices
        self._pending_other: list[tuple[int, Statement]] = []
        self._statement_index = 0

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

        # Visit children first to populate _expr_map with type info
        result = self.visitChildren(ctx)

        # Get the type from the expression
        expr_interval = ctx.expression().getSourceInterval()
        if expr_interval in self._expr_map:
            value_type = self._expr_map[expr_interval].type
        else:
            # Fallback: try to parse the literal directly
            value_type = parse_literal(value)

        # Pass 1: Collect raw assignment info
        raw = RawAssignment(
            var_name=var_name,
            value=value,
            value_type=value_type,
            index=self._statement_index
        )
        self._pending_assignments.append(raw)
        self._statement_index += 1

        return result

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
            self._pending_other.append((self._statement_index, stmt))
            self._statement_index += 1

        return self.visitChildren(ctx)

    def finalize(self) -> None:
        """
        Pass 2: Process collected assignments and generate final statements.

        Determines for each assignment:
        - DECLARATION: First time seeing this variable
        - REASSIGNMENT: Same variable, same type as current
        - SHADOW: Same variable, different type (requires new let)

        Also determines which declarations need 'mut' (if they have
        same-type reassignments following them).
        """
        # Track variable state: var_name -> (current_type, declaration_index)
        var_state: dict[str, tuple[BaseType, int]] = {}

        # First pass through assignments: determine kind for each
        assignment_info: list[tuple[RawAssignment, AssignmentKind]] = []

        for raw in self._pending_assignments:
            if raw.var_name not in var_state:
                # First time seeing this variable - it's a declaration
                assignment_info.append((raw, AssignmentKind.DECLARATION))
                var_state[raw.var_name] = (raw.value_type, raw.index)
            else:
                current_type, _ = var_state[raw.var_name]
                if raw.value_type == current_type:
                    # Same type - it's a reassignment
                    assignment_info.append((raw, AssignmentKind.REASSIGNMENT))
                else:
                    # Different type - it's a shadow (new declaration)
                    assignment_info.append((raw, AssignmentKind.SHADOW))
                    var_state[raw.var_name] = (raw.value_type, raw.index)

        # Second pass: determine which declarations need 'mut'
        # A declaration needs mut if there's a REASSIGNMENT for the same var after it
        # (before the next SHADOW or end)
        needs_mut: set[int] = set()  # Set of declaration indices that need mut

        # Reset var_state to track declaration indices
        var_state.clear()

        for raw, kind in assignment_info:
            if kind == AssignmentKind.DECLARATION or kind == AssignmentKind.SHADOW:
                # This is a (new) declaration, track it
                var_state[raw.var_name] = (raw.value_type, raw.index)
            elif kind == AssignmentKind.REASSIGNMENT:
                # This is a reassignment - mark the corresponding declaration as needing mut
                if raw.var_name in var_state:
                    _, decl_index = var_state[raw.var_name]
                    needs_mut.add(decl_index)

        # Build the final statements list
        # Create a dict of index -> Statement for assignments
        assignment_statements: dict[int, Statement] = {}

        for raw, kind in assignment_info:
            stmt = VariableAssignment(
                variable_name=raw.var_name,
                value=raw.value,
                kind=kind,
                needs_mut=(raw.index in needs_mut)
            )
            assignment_statements[raw.index] = stmt

        # Merge assignments and other statements in order
        all_statements: dict[int, Statement] = {}
        all_statements.update(assignment_statements)
        for idx, stmt in self._pending_other:
            all_statements[idx] = stmt

        # Sort by index and populate self.statements
        self.statements = [all_statements[i] for i in sorted(all_statements.keys())]
