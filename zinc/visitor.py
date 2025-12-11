"""Visitor for the Zinc compiler - transforms parse tree to AST and generates code."""

from dataclasses import dataclass
from typing import Union

from zinc.parser.zincParser import zincParser as ZincParser
from zinc.parser.zincVisitor import zincVisitor as ZincVisitor

from zinc.ast.types import BaseType, TypeInfo, parse_literal
from zinc.ast.expressions import (
    Expression,
    LiteralExpr,
    IdentifierExpr,
    BinaryExpr,
    UnaryExpr,
    ParenExpr,
)
from zinc.ast.statements import (
    Statement,
    AssignmentKind,
    VariableAssignment,
    PrintStatement,
)
from zinc.ast.symbols import Scope


INDENT = "    "


@dataclass
class RawAssignment:
    """Raw assignment info collected during Pass 1."""

    var_name: str
    value: Union[Expression, str]  # Expression AST or raw string
    value_type: BaseType
    stmt_index: int  # Position in statement list (for tracking order)


class Program:
    """Represents a compiled Zinc program."""

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
    """Visitor that transforms ANTLR parse tree into Zinc AST."""

    def __init__(self) -> None:
        self._scope = Scope()
        self.statements: list[Statement] = []
        # Pass 1: Collect raw assignments before processing
        self._pending_assignments: list[RawAssignment] = []
        # Track non-assignment statements with their indices
        self._pending_other: list[tuple[int, Statement]] = []
        self._statement_index = 0

    # ============================================================
    # Expression Visitors - Return Expression AST nodes
    # ============================================================

    def visitLiteral(self, ctx: ZincParser.LiteralContext) -> Expression:
        """Visit a literal and return a LiteralExpr."""
        text = ctx.getText()
        base_type = parse_literal(text)
        type_info = TypeInfo(base_type)
        return LiteralExpr(value=text, type_info=type_info)

    def visitPrimaryExpression(self, ctx: ZincParser.PrimaryExpressionContext) -> Expression:
        """Handle primary expressions (literals, identifiers, etc.)."""
        # Literal
        if ctx.literal():
            return self.visit(ctx.literal())

        # Identifier (variable reference)
        if ctx.IDENTIFIER():
            name = ctx.IDENTIFIER().getText()
            # Look up variable type in scope
            symbol = self._scope.lookup(name)
            type_info = symbol.type_info if symbol else TypeInfo(BaseType.UNKNOWN)
            return IdentifierExpr(name=name, type_info=type_info)

        # Fallback for other cases (array, struct instantiation, etc.)
        return LiteralExpr(value=ctx.getText(), type_info=TypeInfo(BaseType.UNKNOWN))

    def visitPrimaryExpr(self, ctx: ZincParser.PrimaryExprContext) -> Expression:
        """Visit primary expression wrapper."""
        return self.visit(ctx.primaryExpression())

    def visitParenExpr(self, ctx: ZincParser.ParenExprContext) -> Expression:
        """Handle parenthesized expressions."""
        inner = self.visit(ctx.expression())
        return ParenExpr(inner=inner, type_info=inner.type_info)

    def visitAdditiveExpr(self, ctx: ZincParser.AdditiveExprContext) -> Expression:
        """Handle addition and subtraction: expr ('+' | '-') expr"""
        left = self.visit(ctx.expression(0))
        right = self.visit(ctx.expression(1))

        # Get operator from the middle child (index 1)
        operator = ctx.getChild(1).getText()

        # Infer result type
        left_type = left.type_info if left.type_info else TypeInfo(BaseType.UNKNOWN)
        right_type = right.type_info if right.type_info else TypeInfo(BaseType.UNKNOWN)
        result_type = TypeInfo.promote(left_type, right_type)

        return BinaryExpr(
            left=left,
            operator=operator,
            right=right,
            type_info=result_type,
        )

    def visitMultiplicativeExpr(self, ctx: ZincParser.MultiplicativeExprContext) -> Expression:
        """Handle multiplication, division, modulo: expr ('*' | '/' | '%') expr"""
        left = self.visit(ctx.expression(0))
        right = self.visit(ctx.expression(1))

        # Get operator from the middle child (index 1)
        operator = ctx.getChild(1).getText()

        # Infer result type
        left_type = left.type_info if left.type_info else TypeInfo(BaseType.UNKNOWN)
        right_type = right.type_info if right.type_info else TypeInfo(BaseType.UNKNOWN)
        result_type = TypeInfo.promote(left_type, right_type)

        return BinaryExpr(
            left=left,
            operator=operator,
            right=right,
            type_info=result_type,
        )

    def visitUnaryExpr(self, ctx: ZincParser.UnaryExprContext) -> Expression:
        """Handle unary expressions: ('-' | '!' | 'not') expr"""
        operand = self.visit(ctx.expression())
        operator = ctx.getChild(0).getText()

        # Type inference for unary
        if operator == "-":
            result_type = operand.type_info if operand.type_info else TypeInfo(BaseType.UNKNOWN)
        else:  # '!' or 'not'
            result_type = TypeInfo(BaseType.BOOLEAN)

        return UnaryExpr(
            operator=operator,
            operand=operand,
            type_info=result_type,
        )

    # ============================================================
    # Statement Visitors
    # ============================================================

    def visitProgram(self, ctx):
        """Visit the program root."""
        return self.visitChildren(ctx)

    def visitFunctionDeclaration(self, ctx: ZincParser.FunctionDeclarationContext):
        """Visit function declaration, creating a new scope."""
        # Add a new scope for the function
        self._scope = self._scope.enter_scope()

        result = super().visitFunctionDeclaration(ctx)
        self._scope = self._scope.exit_scope()
        return result

    def visitVariableAssignment(self, ctx):
        """Visit variable assignment, building Expression AST."""
        var_name = ctx.assignmentTarget().getText()

        # Visit expression to get Expression AST
        expr = self.visit(ctx.expression())

        # Get type from expression
        if isinstance(expr, Expression) and expr.type_info:
            value_type = expr.type_info.base
            value = expr
        else:
            # Fallback to raw text
            value = ctx.expression().getText()
            try:
                value_type = parse_literal(value)
            except ValueError:
                value_type = BaseType.UNKNOWN

        # Define variable in scope for future lookups
        self._scope.define(var_name, TypeInfo(value_type))

        # Pass 1: Collect raw assignment info
        raw = RawAssignment(
            var_name=var_name,
            value=value,
            value_type=value_type,
            stmt_index=self._statement_index,
        )
        self._pending_assignments.append(raw)
        self._statement_index += 1

        return None  # Don't continue visiting children

    def visitFunctionCallExpr(self, ctx: ZincParser.FunctionCallExprContext):
        """Visit function call expression."""
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

    # ============================================================
    # Pass 2: Finalization
    # ============================================================

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
                var_state[raw.var_name] = (raw.value_type, raw.stmt_index)
            else:
                current_type, _ = var_state[raw.var_name]
                if raw.value_type == current_type:
                    # Same type - it's a reassignment
                    assignment_info.append((raw, AssignmentKind.REASSIGNMENT))
                else:
                    # Different type - it's a shadow (new declaration)
                    assignment_info.append((raw, AssignmentKind.SHADOW))
                    var_state[raw.var_name] = (raw.value_type, raw.stmt_index)

        # Second pass: determine which declarations need 'mut'
        # A declaration needs mut if there's a REASSIGNMENT for the same var after it
        # (before the next SHADOW or end)
        needs_mut: set[int] = set()  # Set of declaration indices that need mut

        # Reset var_state to track declaration indices
        var_state.clear()

        for raw, kind in assignment_info:
            if kind == AssignmentKind.DECLARATION or kind == AssignmentKind.SHADOW:
                # This is a (new) declaration, track it
                var_state[raw.var_name] = (raw.value_type, raw.stmt_index)
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
                needs_mut=(raw.stmt_index in needs_mut),
            )
            assignment_statements[raw.stmt_index] = stmt

        # Merge assignments and other statements in order
        all_statements: dict[int, Statement] = {}
        all_statements.update(assignment_statements)
        for idx, stmt in self._pending_other:
            all_statements[idx] = stmt

        # Sort by index and populate self.statements
        self.statements = [all_statements[i] for i in sorted(all_statements.keys())]
