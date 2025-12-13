"""Visitor for the Zinc compiler - transforms parse tree to AST and generates code."""

from dataclasses import dataclass
from typing import Sequence, Union

from zinc.parser.zincParser import zincParser as ZincParser
from zinc.parser.zincVisitor import zincVisitor as ZincVisitor

from zinc.ast.types import BaseType, TypeInfo, parse_literal, type_to_rust, ChannelTypeInfo, ArrayTypeInfo
from zinc.ast.expressions import (
    Expression,
    LiteralExpr,
    IdentifierExpr,
    BinaryExpr,
    UnaryExpr,
    ParenExpr,
    CallExpr,
    ChannelCreateExpr,
    ChannelReceiveExpr,
    ArrayLiteralExpr,
    IndexExpr,
    MethodCallExpr,
    RangeExpr,
)
from zinc.ast.structs import (
    StructField,
    StructMethod,
    StructDeclaration,
    StructInstantiationExpr,
    SelfExpr,
    MemberAccessExpr,
    StaticMethodCallExpr,
    FieldModifier,
    is_known_type,
    zinc_type_to_base,
)
from zinc.ast.statements import (
    Statement,
    AssignmentKind,
    VariableAssignment,
    PrintStatement,
    IfBranch,
    IfStatement,
    Parameter,
    FunctionDeclaration,
    ReturnStatement,
    SpawnStatement,
    ChannelSendStatement,
    ChannelDeclaration,
    MethodCallStatement,
    ForStatement,
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


@dataclass
class CallSite:
    """Records a function call with resolved argument types."""

    func_name: str
    arg_types: tuple[BaseType, ...]  # Tuple for hashability
    call_expr: "CallExpr"  # Reference to update mangled_name later


@dataclass
class RawChannelDeclaration:
    """Raw channel declaration info collected during Pass 1."""

    var_name: str
    channel_info: ChannelTypeInfo
    stmt_index: int


class Program:
    """Represents a compiled Zinc program."""

    def __init__(
        self,
        scope: Scope,
        statements: Sequence[Statement],
        monomorphized: Sequence[Statement] | None = None,
        uses_spawn: bool = False,
    ):
        self.scope = scope
        self.statements = statements
        self.monomorphized = monomorphized or []
        self.uses_spawn = uses_spawn

    def render(self) -> str:
        """Render the program as valid Rust code."""
        rust_code = ""

        # First render monomorphized functions (they need to come before main)
        for func in self.monomorphized:
            func_code = func.render()
            if func_code:  # Skip empty (template functions)
                rust_code += func_code + "\n"

        # Then render regular statements (including main)
        for stmt in self.statements:
            # Special handling for main function when spawn is used
            if isinstance(stmt, FunctionDeclaration) and stmt.name == "main" and self.uses_spawn:
                rust_code += self._render_async_main(stmt)
            else:
                stmt_code = stmt.render()
                if stmt_code:  # Skip empty (template functions render as "")
                    rust_code += stmt_code + "\n"

        return rust_code

    def _render_async_main(self, main_func: FunctionDeclaration) -> str:
        """Render main as an async function with tokio runtime."""
        lines = ["#[tokio::main]", "async fn main() {"]
        for stmt in main_func.body:
            for line in stmt.render().split("\n"):
                lines.append(f"    {line}")
        lines.append("}")
        return "\n".join(lines) + "\n"


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

        # Monomorphization tracking
        self._function_templates: dict[str, FunctionDeclaration] = {}  # Untyped functions
        self._call_sites: list[CallSite] = []  # All function calls with arg types
        self._monomorphized: list[FunctionDeclaration] = []  # Generated typed functions

        # Spawn tracking
        self._spawned_functions: set[str] = set()  # Mangled names of functions called via spawn
        self._uses_spawn: bool = False  # True if any spawn statement is used

        # Channel tracking
        self._channel_vars: dict[str, ChannelTypeInfo] = {}  # var_name -> channel info
        self._channel_usages: dict[str, set[str]] = {}  # var_name -> {"sender", "receiver"}
        self._pending_channel_decls: list[RawChannelDeclaration] = []  # Channel declarations
        self._channel_name_map: dict[str, tuple[str, str]] = {}  # var_name -> (sender_name, receiver_name)

        # Array tracking
        self._array_vars: dict[str, ArrayTypeInfo] = {}  # var_name -> array info
        self._array_push_vars: set[str] = set()  # vars that have .push() called
        self._array_assignments: dict[str, VariableAssignment] = {}  # var_name -> assignment (for mut fixup)

        # Struct tracking
        self._struct_definitions: dict[str, StructDeclaration] = {}  # name -> struct
        self._current_struct: str | None = None  # When visiting struct body
        self._current_struct_fields: list[StructField] | None = None  # Fields of current struct
        self._current_struct_method: str | None = None  # Current method being visited
        self._struct_method_self_usage: dict[str, set[str]] = {}  # method_name -> {"read", "write"}
        self._struct_instance_vars: dict[str, str] = {}  # var_name -> struct type name
        self._struct_mut_method_vars: set[str] = set()  # vars with &mut self method calls

    # ============================================================
    # Expression Visitors - Return Expression AST nodes
    # ============================================================

    def visitLiteral(self, ctx: ZincParser.LiteralContext) -> Expression:
        """Visit a literal and return a LiteralExpr."""
        text = ctx.getText()
        base_type = parse_literal(text)
        type_info = TypeInfo(base_type)

        # Track self usage in string interpolations like "{self.field}"
        if base_type == BaseType.STRING and self._current_struct_method:
            import re
            if re.search(r"\{self\.", text):
                self._struct_method_self_usage[self._current_struct_method].add("read")

        return LiteralExpr(value=text, type_info=type_info)

    def visitPrimaryExpression(self, ctx: ZincParser.PrimaryExpressionContext) -> Expression:
        """Handle primary expressions (literals, identifiers, etc.)."""
        # Literal
        if ctx.literal():
            return self.visit(ctx.literal())

        # Self keyword
        if ctx.getText() == "self":
            return SelfExpr(type_info=TypeInfo(BaseType.STRUCT))

        # Identifier (variable reference)
        if ctx.IDENTIFIER():
            name = ctx.IDENTIFIER().getText()

            # Look up variable type in scope
            symbol = self._scope.lookup(name)
            type_info = symbol.type_info if symbol else TypeInfo(BaseType.UNKNOWN)
            return IdentifierExpr(name=name, type_info=type_info)

        # Array literal
        if ctx.arrayLiteral():
            return self.visit(ctx.arrayLiteral())

        # Struct instantiation
        if ctx.structInstantiation():
            return self.visit(ctx.structInstantiation())

        # Fallback for other cases
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

    def visitChannelReceiveExpr(self, ctx: ZincParser.ChannelReceiveExprContext) -> Expression:
        """Handle channel receive: <- expr"""
        channel_expr = self.visit(ctx.expression())

        # Track that this channel variable is used as a receiver
        if isinstance(channel_expr, IdentifierExpr):
            var_name = channel_expr.name
            if var_name not in self._channel_usages:
                self._channel_usages[var_name] = set()
            self._channel_usages[var_name].add("receiver")

            # Rewrite the identifier to use the receiver name
            if var_name in self._channel_name_map:
                _, receiver_name = self._channel_name_map[var_name]
                channel_expr = IdentifierExpr(name=receiver_name, type_info=channel_expr.type_info)

        return ChannelReceiveExpr(channel=channel_expr)

    def visitArrayLiteral(self, ctx: ZincParser.ArrayLiteralContext) -> Expression:
        """Visit array literal: [expr, expr, ...]."""
        elements = []
        for expr_ctx in ctx.expression():
            elements.append(self.visit(expr_ctx))

        # Infer element type from first element
        elem_type = BaseType.UNKNOWN
        if elements and elements[0].type_info:
            elem_type = elements[0].type_info.base

        array_info = ArrayTypeInfo(element_type=elem_type, is_vector=False)

        return ArrayLiteralExpr(
            elements=elements,
            array_info=array_info,
            type_info=TypeInfo(BaseType.ARRAY),
        )

    def visitIndexAccessExpr(self, ctx: ZincParser.IndexAccessExprContext) -> Expression:
        """Visit index access: expr[expr]."""
        target = self.visit(ctx.expression(0))
        index = self.visit(ctx.expression(1))

        # Infer type from array element type if known
        result_type = None
        if isinstance(target, IdentifierExpr) and target.name in self._array_vars:
            array_info = self._array_vars[target.name]
            result_type = TypeInfo(array_info.element_type)

        return IndexExpr(target=target, index=index, type_info=result_type)

    def visitRangeExpr(self, ctx: ZincParser.RangeExprContext) -> Expression:
        """Visit range expression: start..end or start..=end."""
        start = self.visit(ctx.expression(0))
        end = self.visit(ctx.expression(1))

        # Check if inclusive (..=) or exclusive (..)
        # The grammar has: expression ('..' | '..=') expression
        inclusive = ctx.DOTDOTEQ() is not None

        return RangeExpr(
            start=start,
            end=end,
            inclusive=inclusive,
            type_info=TypeInfo(BaseType.INTEGER),
        )

    def visitRelationalExpr(self, ctx: ZincParser.RelationalExprContext) -> Expression:
        """Handle relational comparisons: expr ('<' | '<=' | '>' | '>=') expr"""
        left = self.visit(ctx.expression(0))
        right = self.visit(ctx.expression(1))

        # Get operator from the middle child (index 1)
        operator = ctx.getChild(1).getText()

        # Relational expressions always return boolean
        return BinaryExpr(
            left=left,
            operator=operator,
            right=right,
            type_info=TypeInfo(BaseType.BOOLEAN),
        )

    def visitEqualityExpr(self, ctx: ZincParser.EqualityExprContext) -> Expression:
        """Handle equality comparisons: expr ('==' | '!=') expr"""
        left = self.visit(ctx.expression(0))
        right = self.visit(ctx.expression(1))

        # Get operator from the middle child (index 1)
        operator = ctx.getChild(1).getText()

        # Equality expressions always return boolean
        return BinaryExpr(
            left=left,
            operator=operator,
            right=right,
            type_info=TypeInfo(BaseType.BOOLEAN),
        )

    def visitMemberAccessExpr(self, ctx: ZincParser.MemberAccessExprContext) -> Expression:
        """Handle member access: expr.member"""
        target = self.visit(ctx.expression())
        member = ctx.IDENTIFIER().getText()

        # Track self usage in struct methods
        if isinstance(target, SelfExpr) and self._current_struct_method:
            # Reading self.field counts as "read"
            self._struct_method_self_usage[self._current_struct_method].add("read")

        # Check if this is a static method call on a struct type (MyStruct.method)
        if isinstance(target, IdentifierExpr) and target.name in self._struct_definitions:
            # This will be a static method call - return StaticMethodCallExpr
            # (arguments will be added by visitFunctionCallExpr)
            struct_decl = self._struct_definitions[target.name]
            return StaticMethodCallExpr(
                struct_name=target.name,
                method_name=member,
                arguments=[],
                type_info=None,
                struct_decl=struct_decl,
            )

        return MemberAccessExpr(target=target, member=member)

    # ============================================================
    # Statement Visitors
    # ============================================================

    def visitProgram(self, ctx):
        """Visit the program root."""
        return self.visitChildren(ctx)

    def visitFunctionDeclaration(self, ctx: ZincParser.FunctionDeclarationContext):
        """Visit function declaration, creating a new scope."""
        name = ctx.IDENTIFIER().getText()

        # Parse parameters
        parameters = []
        if ctx.parameterList():
            for param_ctx in ctx.parameterList().parameter():
                param_name = param_ctx.IDENTIFIER().getText()
                type_ann = None
                if param_ctx.type_():
                    type_ann = param_ctx.type_().getText()
                parameters.append(Parameter(name=param_name, type_annotation=type_ann))

        # Enter new scope for function body
        self._scope = self._scope.enter_scope()

        # Add parameters to scope
        for param in parameters:
            self._scope.define(param.name, TypeInfo(BaseType.UNKNOWN))

        # Visit function body
        body = self._visit_block(ctx.block())

        self._scope = self._scope.exit_scope()

        # Create function declaration statement
        stmt = FunctionDeclaration(name=name, parameters=parameters, body=body)

        # Check if this is a function that needs monomorphization (has untyped params)
        # "main" is special - never monomorphize it
        has_untyped_params = any(p.type_annotation is None for p in parameters)
        if name != "main" and has_untyped_params:
            # Store as template for later monomorphization
            stmt.is_template = True
            self._function_templates[name] = stmt

        self._pending_other.append((self._statement_index, stmt))
        self._statement_index += 1

        return None

    def visitStructDeclaration(self, ctx: ZincParser.StructDeclarationContext):
        """Visit struct declaration."""
        name = ctx.IDENTIFIER().getText()
        self._current_struct = name

        fields: list[StructField] = []
        methods: list[StructMethod] = []

        # Visit struct body - collect fields first
        body_ctx = ctx.structBody()
        for member_ctx in body_ctx.structMember():
            if member_ctx.structField():
                field = self._visit_struct_field(member_ctx.structField())
                fields.append(field)

        # Store fields for parameter type inference
        self._current_struct_fields = fields

        # Pre-register struct (without methods) so struct instantiation in method bodies can find it
        preliminary_struct_decl = StructDeclaration(name=name, fields=fields, methods=[])
        self._struct_definitions[name] = preliminary_struct_decl

        # Then visit methods (now fields are available for type inference)
        for member_ctx in body_ctx.structMember():
            if member_ctx.functionDeclaration():
                method = self._visit_struct_method(member_ctx.functionDeclaration())
                methods.append(method)

        self._current_struct = None
        self._current_struct_fields = None

        # Update struct declaration with methods
        struct_decl = StructDeclaration(name=name, fields=fields, methods=methods)
        self._struct_definitions[name] = struct_decl

        # Post-process: mark static method calls on self
        static_methods = {m.name for m in methods if m.is_static}
        self._mark_static_method_calls(methods, static_methods)

        # Add to pending statements
        self._pending_other.append((self._statement_index, struct_decl))
        self._statement_index += 1

        return None

    def _visit_struct_field(self, ctx) -> StructField:
        """Parse a struct field declaration."""
        # Check for const modifier
        is_const = ctx.getChild(0).getText() == "const" if ctx.getChildCount() > 0 else False

        # Get field name - it's after 'const' if present, otherwise first
        if is_const:
            name = ctx.IDENTIFIER().getText()
        else:
            name = ctx.IDENTIFIER().getText()

        type_ann = None
        default_value = None
        resolved_type = None

        # After the colon, we have either a type or an expression
        # Check if there's a type() context
        if ctx.type_():
            type_ann = ctx.type_().getText()
            resolved_type = zinc_type_to_base(type_ann)
        elif ctx.expression():
            default_value = self.visit(ctx.expression())
            if default_value and default_value.type_info:
                resolved_type = default_value.type_info.base

        modifier = FieldModifier.CONST if is_const else FieldModifier.NONE

        return StructField(
            name=name,
            type_annotation=type_ann,
            default_value=default_value,
            modifier=modifier,
            resolved_type=resolved_type,
        )

    def _visit_struct_method(self, ctx: ZincParser.FunctionDeclarationContext) -> StructMethod:
        """Parse a struct method and determine if static/instance."""
        name = ctx.IDENTIFIER().getText()
        self._current_struct_method = name
        self._struct_method_self_usage[name] = set()

        # Parse parameters
        parameters: list[Parameter] = []
        if ctx.parameterList():
            for param_ctx in ctx.parameterList().parameter():
                param_name = param_ctx.IDENTIFIER().getText()
                type_ann = None
                if param_ctx.type_():
                    type_ann = param_ctx.type_().getText()
                parameters.append(Parameter(name=param_name, type_annotation=type_ann))

        # Enter scope for method body
        self._scope = self._scope.enter_scope()

        # Add parameters to scope
        for param in parameters:
            self._scope.define(param.name, TypeInfo(BaseType.UNKNOWN))

        # Visit method body - this will track self usage
        body = self._visit_block(ctx.block())

        self._scope = self._scope.exit_scope()

        # Infer parameter types from usage in method body
        self._infer_method_param_types(parameters, body)

        # Analyze self usage to determine static vs instance
        self_usage = self._struct_method_self_usage.get(name, set())
        is_static = len(self_usage) == 0

        if is_static:
            self_mutability = None
        elif "write" in self_usage:
            self_mutability = "&mut self"
        else:
            self_mutability = "&self"

        self._current_struct_method = None

        # Infer return type from body
        return_type = self._infer_method_return_type(body)

        return StructMethod(
            name=name,
            parameters=parameters,
            body=body,
            return_type=return_type,
            is_static=is_static,
            self_mutability=self_mutability,
        )

    def _infer_method_return_type(self, body: list[Statement]) -> str | None:
        """Infer return type from method body."""
        # Build field name -> type mapping if we're in a struct
        field_types: dict[str, str] = {}
        if self._current_struct and self._current_struct_fields:
            for f in self._current_struct_fields:
                # Use rust_type() which prefers explicit annotation over resolved type
                field_types[f.name] = f.rust_type()

        def get_expr_type(expr: Expression) -> str | None:
            """Get the type of an expression."""
            if isinstance(expr, MemberAccessExpr):
                if isinstance(expr.target, SelfExpr):
                    return field_types.get(expr.member)
            if isinstance(expr, BinaryExpr):
                # For binary expr, get type from operands (assumes same type for arithmetic)
                left_type = get_expr_type(expr.left)
                if left_type:
                    return left_type
                right_type = get_expr_type(expr.right)
                if right_type:
                    return right_type
            if expr.type_info:
                return type_to_rust(expr.type_info.base)
            return None

        for stmt in body:
            if isinstance(stmt, ReturnStatement) and stmt.value:
                # Check if returning a struct instantiation of our own type
                if isinstance(stmt.value, StructInstantiationExpr):
                    if self._current_struct and stmt.value.struct_name == self._current_struct:
                        return "Self"
                    return stmt.value.struct_name
                # Try to infer type from expression
                inferred_type = get_expr_type(stmt.value)
                if inferred_type:
                    return inferred_type
        return None

    def _mark_static_method_calls(self, methods: list[StructMethod], static_methods: set[str]) -> None:
        """Mark MethodCallExpr nodes that call static methods on self.

        After all methods are processed, we know which ones are static.
        Go through all method bodies and mark self.static_method() calls.
        """
        from zinc.ast.structs import SelfExpr

        def visit_expr(expr: Expression) -> None:
            """Recursively visit expressions to find method calls on self."""
            if isinstance(expr, MethodCallExpr):
                if isinstance(expr.target, SelfExpr) and expr.method_name in static_methods:
                    expr.is_static = True
                # Visit arguments
                for arg in expr.arguments:
                    visit_expr(arg)
            elif isinstance(expr, BinaryExpr):
                visit_expr(expr.left)
                visit_expr(expr.right)
            elif isinstance(expr, UnaryExpr):
                visit_expr(expr.operand)
            elif isinstance(expr, ParenExpr):
                visit_expr(expr.inner)
            elif isinstance(expr, CallExpr):
                for arg in expr.arguments:
                    visit_expr(arg)

        def visit_stmt(stmt: Statement) -> None:
            """Recursively visit statements to find method calls on self."""
            if isinstance(stmt, VariableAssignment):
                if isinstance(stmt.value, Expression):
                    visit_expr(stmt.value)
            elif isinstance(stmt, ReturnStatement):
                if stmt.value:
                    visit_expr(stmt.value)
            elif isinstance(stmt, IfStatement):
                for branch in stmt.branches:
                    visit_expr(branch.condition)
                    for s in branch.body:
                        visit_stmt(s)
                if stmt.else_body:
                    for s in stmt.else_body:
                        visit_stmt(s)

        for method in methods:
            for stmt in method.body:
                visit_stmt(stmt)

    def _infer_method_param_types(self, parameters: list[Parameter], body: list[Statement]) -> None:
        """Infer parameter types from usage in method body.

        Inference sources:
        1. Parameter used in struct field init: infer from field type
        2. Parameter assigned to self.field: infer from field type
        3. Parameter in binary expr with self.field: infer from field type
        4. Parameter in binary expr with literal: infer from literal type
        """
        if not self._current_struct or not self._current_struct_fields:
            return

        # Build field name -> type mapping
        field_types: dict[str, str] = {}
        for f in self._current_struct_fields:
            # Use rust_type() which prefers explicit annotation over resolved type
            rust_type = f.rust_type()
            if rust_type != "unknown":
                field_types[f.name] = rust_type

        # Build param name -> Parameter mapping
        param_map = {p.name: p for p in parameters}

        def get_expr_type(expr: Expression) -> str | None:
            """Get the type of an expression if known."""
            if isinstance(expr, MemberAccessExpr):
                if isinstance(expr.target, SelfExpr):
                    return field_types.get(expr.member)
            if expr.type_info:
                return type_to_rust(expr.type_info.base)
            return None

        def infer_from_binary_expr(expr: BinaryExpr) -> None:
            """Infer param types from binary expressions like a + b or self.x + param."""
            left = expr.left
            right = expr.right
            left_is_param = isinstance(left, IdentifierExpr) and left.name in param_map
            right_is_param = isinstance(right, IdentifierExpr) and right.name in param_map

            # If one side is a param and other has known type, infer
            if left_is_param and not right_is_param:
                right_type = get_expr_type(right)
                if right_type and isinstance(left, IdentifierExpr):
                    param = param_map[left.name]
                    if not param.type_annotation and not param.resolved_type:
                        param.resolved_type = right_type
            elif right_is_param and not left_is_param:
                left_type = get_expr_type(left)
                if left_type and isinstance(right, IdentifierExpr):
                    param = param_map[right.name]
                    if not param.type_annotation and not param.resolved_type:
                        param.resolved_type = left_type

            # Recurse into nested binary expressions
            if isinstance(left, BinaryExpr):
                infer_from_binary_expr(left)
            if isinstance(right, BinaryExpr):
                infer_from_binary_expr(right)

        def scan_expr(expr: Expression) -> None:
            """Recursively scan expressions for type inference."""
            if isinstance(expr, BinaryExpr):
                infer_from_binary_expr(expr)
            elif isinstance(expr, ParenExpr):
                scan_expr(expr.inner)

        def scan_stmt(stmt: Statement) -> None:
            """Scan a statement for parameter type inference opportunities."""
            if isinstance(stmt, ReturnStatement) and stmt.value:
                if isinstance(stmt.value, StructInstantiationExpr):
                    for field_name, field_value in stmt.value.field_inits.items():
                        # Check if field_value is an identifier referencing a parameter
                        if isinstance(field_value, IdentifierExpr):
                            param_name = field_value.name
                            if param_name in param_map and field_name in field_types:
                                param = param_map[param_name]
                                if not param.type_annotation and not param.resolved_type:
                                    param.resolved_type = field_types[field_name]
                else:
                    scan_expr(stmt.value)
            elif isinstance(stmt, VariableAssignment):
                # Check for self.field = param assignments
                var_name = stmt.variable_name
                if var_name.startswith("self."):
                    field_name = var_name[5:]  # Remove "self." prefix
                    if field_name in field_types:
                        # Check if the value is a parameter identifier
                        if isinstance(stmt.value, IdentifierExpr):
                            param_name = stmt.value.name
                            if param_name in param_map:
                                param = param_map[param_name]
                                if not param.type_annotation and not param.resolved_type:
                                    param.resolved_type = field_types[field_name]
                        # Also check binary expressions in assignment
                        elif isinstance(stmt.value, BinaryExpr):
                            scan_expr(stmt.value)

        # Scan body for type inference opportunities
        for stmt in body:
            scan_stmt(stmt)

    def visitStructInstantiation(self, ctx: ZincParser.StructInstantiationContext) -> Expression:
        """Visit struct literal: MyStruct { a: 1, b: 2 }."""
        struct_name = ctx.IDENTIFIER().getText()

        field_inits: dict[str, Expression] = {}
        for field_ctx in ctx.fieldInit():
            field_name = field_ctx.IDENTIFIER().getText()
            field_value = self.visit(field_ctx.expression())
            field_inits[field_name] = field_value

        # Look up struct declaration for default values
        struct_decl = self._struct_definitions.get(struct_name)

        return StructInstantiationExpr(
            struct_name=struct_name,
            field_inits=field_inits,
            type_info=TypeInfo(BaseType.STRUCT),
            struct_decl=struct_decl,
        )

    def visitVariableAssignment(self, ctx):
        """Visit variable assignment, building Expression AST."""
        var_name = ctx.assignmentTarget().getText()

        # Visit expression to get Expression AST
        expr = self.visit(ctx.expression())

        # Handle channel creation specially
        if isinstance(expr, ChannelCreateExpr):
            # Ensure channel_info exists
            channel_info = expr.channel_info or ChannelTypeInfo()

            # Track channel variable and its info
            self._channel_vars[var_name] = channel_info
            self._channel_usages[var_name] = set()

            # Define in scope so lookups know this is a channel
            self._scope.define(var_name, TypeInfo(BaseType.CHANNEL))

            # Store as pending channel declaration (will be finalized later)
            raw_chan = RawChannelDeclaration(
                var_name=var_name,
                channel_info=channel_info,
                stmt_index=self._statement_index,
            )
            self._pending_channel_decls.append(raw_chan)
            self._statement_index += 1
            return None

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

        # Handle channel receive expressions
        if isinstance(expr, ChannelReceiveExpr):
            value_type = BaseType.UNKNOWN  # Will be inferred during finalization

        # Handle array literal - track for push detection
        if isinstance(expr, ArrayLiteralExpr):
            array_info = expr.array_info or ArrayTypeInfo()
            self._array_vars[var_name] = array_info
            value_type = BaseType.ARRAY

        # Track struct instance variables for mutability analysis
        if isinstance(expr, StructInstantiationExpr):
            self._struct_instance_vars[var_name] = expr.struct_name
        elif isinstance(expr, StaticMethodCallExpr):
            # e.g., counter = Counter.new(...)
            struct_decl = self._struct_definitions.get(expr.struct_name)
            if struct_decl:
                # Check if the method returns Self
                method = next((m for m in struct_decl.methods if m.name == expr.method_name), None)
                if method and method.return_type == "Self":
                    self._struct_instance_vars[var_name] = expr.struct_name

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

    def visitFunctionCallExpr(self, ctx: ZincParser.FunctionCallExprContext) -> Expression | None:
        """Visit function call expression."""
        # Get the callee expression context (not visited yet)
        callee_ctx = ctx.expression()

        # Get the arguments as Expression AST nodes
        arguments = []
        if ctx.argumentList():
            for arg_expr in ctx.argumentList().expression():
                arguments.append(self.visit(arg_expr))

        # Check if this is a method call (expr.method(...))
        if isinstance(callee_ctx, ZincParser.MemberAccessExprContext):
            target = self.visit(callee_ctx.expression())
            method_name = callee_ctx.IDENTIFIER().getText()

            # Check if target is a struct type (static method call)
            if isinstance(target, IdentifierExpr) and target.name in self._struct_definitions:
                struct_decl = self._struct_definitions[target.name]
                return StaticMethodCallExpr(
                    struct_name=target.name,
                    method_name=method_name,
                    arguments=arguments,
                    struct_decl=struct_decl,
                )

            # Track .push() calls for array promotion
            if method_name == "push" and isinstance(target, IdentifierExpr):
                var_name = target.name
                self._array_push_vars.add(var_name)

                # Infer element type from first push argument
                if var_name in self._array_vars:
                    array_info = self._array_vars[var_name]
                    array_info.is_vector = True
                    if array_info.element_type == BaseType.UNKNOWN and arguments:
                        if arguments[0].type_info:
                            array_info.element_type = arguments[0].type_info.base

            # Track struct instance method calls that need &mut self
            # Also extract parameter types for automatic type coercion
            param_types: list[str] | None = None
            if isinstance(target, IdentifierExpr):
                var_name = target.name
                if var_name in self._struct_instance_vars:
                    struct_name = self._struct_instance_vars[var_name]
                    struct_decl = self._struct_definitions.get(struct_name)
                    if struct_decl:
                        method = next((m for m in struct_decl.methods if m.name == method_name), None)
                        if method:
                            if method.self_mutability == "&mut self":
                                self._struct_mut_method_vars.add(var_name)
                            # Extract parameter types for coercion
                            param_types = []
                            for p in method.parameters:
                                if p.resolved_type:
                                    param_types.append(p.resolved_type)
                                elif p.type_annotation:
                                    from zinc.ast.structs import zinc_type_to_rust
                                    param_types.append(zinc_type_to_rust(p.type_annotation))
                                else:
                                    param_types.append("unknown")

            return MethodCallExpr(
                target=target,
                method_name=method_name,
                arguments=arguments,
                param_types=param_types,
            )

        # Now visit the callee for regular function calls
        callee = self.visit(callee_ctx)
        func_name = callee_ctx.getText()

        # Handle static method calls (MyStruct.method())
        if isinstance(callee, StaticMethodCallExpr):
            callee.arguments = arguments
            return callee

        # Handle instance method calls on self (self.method())
        if isinstance(callee, MemberAccessExpr) and isinstance(callee.target, SelfExpr):
            # This is self.method() - track as read
            if self._current_struct_method:
                self._struct_method_self_usage[self._current_struct_method].add("read")
            return MethodCallExpr(
                target=callee.target,
                method_name=callee.member,
                arguments=arguments,
            )

        # Handle chan() builtin for channel creation
        if func_name == "chan":
            capacity = arguments[0] if arguments else None
            is_bounded = capacity is not None
            channel_info = ChannelTypeInfo(element_type=BaseType.UNKNOWN, is_bounded=is_bounded)
            return ChannelCreateExpr(capacity=capacity, channel_info=channel_info)

        # If this is a print() call at statement level, create a PrintStatement
        # We check this by seeing if we're being called from top-level statement processing
        if func_name == "print":
            # Convert arguments to raw strings for PrintStatement
            raw_args = [arg_expr.getText() for arg_expr in ctx.argumentList().expression()] if ctx.argumentList() else []
            stmt = PrintStatement(arguments=raw_args)
            self._pending_other.append((self._statement_index, stmt))
            self._statement_index += 1
            return None

        # For other function calls, create CallExpr and track for monomorphization
        call_expr = CallExpr(callee=callee, arguments=arguments)

        # Extract argument types for monomorphization
        arg_types: list[BaseType] = []
        for arg in arguments:
            if isinstance(arg, Expression) and arg.type_info:
                arg_types.append(arg.type_info.base)
            else:
                arg_types.append(BaseType.UNKNOWN)

        # Record call site if this is a user-defined function (not a builtin)
        # We'll resolve this during monomorphization
        self._call_sites.append(CallSite(
            func_name=func_name,
            arg_types=tuple(arg_types),
            call_expr=call_expr,
        ))

        return call_expr

    def visitReturnStatement(self, ctx: ZincParser.ReturnStatementContext):
        """Visit return statement."""
        value = None
        if ctx.expression():
            value = self.visit(ctx.expression())
        return ReturnStatement(value=value)

    def visitSpawnStatement(self, ctx: ZincParser.SpawnStatementContext):
        """Visit spawn statement for concurrent execution."""
        self._uses_spawn = True

        # Get the function name being called
        func_name = ctx.expression().getText()

        # Build the arguments list
        arguments = []
        if ctx.argumentList():
            for arg_expr in ctx.argumentList().expression():
                arguments.append(self.visit(arg_expr))

        # Get the callee expression (function name)
        callee = self.visit(ctx.expression())

        # Create the call expression
        call_expr = CallExpr(callee=callee, arguments=arguments)

        # Extract argument types for monomorphization
        arg_types: list[BaseType] = []
        for arg in arguments:
            if isinstance(arg, Expression) and arg.type_info:
                arg_types.append(arg.type_info.base)
            else:
                arg_types.append(BaseType.UNKNOWN)

        # Record call site for monomorphization (same as regular calls)
        call_site = CallSite(
            func_name=func_name,
            arg_types=tuple(arg_types),
            call_expr=call_expr,
        )
        self._call_sites.append(call_site)

        # Mark that this function is spawned (we'll set the mangled name later)
        # For now, track by func_name + arg_types
        type_suffix = "_".join(type_to_rust(t) for t in arg_types)
        mangled_name = f"{func_name}_{type_suffix}"
        self._spawned_functions.add(mangled_name)

        # Create spawn statement
        stmt = SpawnStatement(call_expr=call_expr)
        self._pending_other.append((self._statement_index, stmt))
        self._statement_index += 1

        return None

    def visitChannelSendStatement(self, ctx: ZincParser.ChannelSendStatementContext):
        """Visit channel send statement: IDENTIFIER '<-' expression"""
        channel_name = ctx.IDENTIFIER().getText()
        value_expr = self.visit(ctx.expression())

        # Track that this channel is used as a sender
        if channel_name not in self._channel_usages:
            self._channel_usages[channel_name] = set()
        self._channel_usages[channel_name].add("sender")

        # Infer element type from the value being sent
        if channel_name in self._channel_vars:
            chan_info = self._channel_vars[channel_name]
            if chan_info.element_type == BaseType.UNKNOWN:
                if isinstance(value_expr, Expression) and value_expr.type_info:
                    chan_info.element_type = value_expr.type_info.base

        stmt = ChannelSendStatement(channel_name=channel_name, value=value_expr)
        self._pending_other.append((self._statement_index, stmt))
        self._statement_index += 1

        return None

    def visitIfStatement(self, ctx: ZincParser.IfStatementContext):
        """Visit if/else statement."""
        branches = []
        else_body = None

        # Get all expressions (conditions) and blocks
        expressions = ctx.expression()
        blocks = ctx.block()

        num_conditions = len(expressions)
        num_blocks = len(blocks)

        # Process each if/else-if branch (one condition per branch)
        for i in range(num_conditions):
            condition = self.visit(expressions[i])
            body_stmts = self._visit_block(blocks[i])
            branches.append(IfBranch(condition=condition, body=body_stmts))

        # Check for else block (more blocks than conditions means there's an else)
        if num_blocks > num_conditions:
            else_body = self._visit_block(blocks[num_blocks - 1])

        stmt = IfStatement(branches=branches, else_body=else_body)
        self._pending_other.append((self._statement_index, stmt))
        self._statement_index += 1

        return None  # Don't continue visiting children

    def visitForStatement(self, ctx: ZincParser.ForStatementContext):
        """Visit for-in loop statement."""
        loop_var = ctx.IDENTIFIER().getText()
        iterable = self.visit(ctx.expression())

        # Enter scope for loop body (loop variable is local)
        self._scope = self._scope.enter_scope()

        # Infer loop variable type from iterable
        loop_var_type = TypeInfo(BaseType.UNKNOWN)
        if isinstance(iterable, IdentifierExpr) and iterable.name in self._array_vars:
            array_info = self._array_vars[iterable.name]
            loop_var_type = TypeInfo(array_info.element_type)
        elif isinstance(iterable, RangeExpr):
            loop_var_type = TypeInfo(BaseType.INTEGER)

        # Define loop variable in scope
        self._scope.define(loop_var, loop_var_type)

        # Visit loop body
        body_stmts = self._visit_block(ctx.block())

        self._scope = self._scope.exit_scope()

        stmt = ForStatement(
            loop_variable=loop_var,
            iterable=iterable,
            body=body_stmts,
        )
        self._pending_other.append((self._statement_index, stmt))
        self._statement_index += 1

        return None  # Don't continue visiting children

    def _visit_block(self, block_ctx) -> list[Statement]:
        """Visit a block and return list of statements."""
        statements = []

        for stmt_ctx in block_ctx.statement():
            # Handle each statement type
            stmt = self._visit_statement(stmt_ctx)
            if stmt:
                statements.append(stmt)

        # Fix up array mutability: arrays with .push() calls need mut
        for var_name in self._array_push_vars:
            if var_name in self._array_assignments:
                assignment = self._array_assignments[var_name]
                assignment.needs_mut = True
                # Also update the ArrayLiteralExpr's array_info
                if isinstance(assignment.value, ArrayLiteralExpr):
                    assignment.value.array_info = self._array_vars.get(var_name)

        # Fix up struct instance mutability: struct vars with &mut self method calls need mut
        for var_name in self._struct_mut_method_vars:
            if var_name in self._array_assignments:  # Reusing array tracking dict
                assignment = self._array_assignments[var_name]
                assignment.needs_mut = True

        return statements

    def _visit_statement(self, stmt_ctx) -> Statement | None:
        """Visit a single statement and return a Statement object."""
        # Check for variable assignment
        if stmt_ctx.variableAssignment():
            var_ctx = stmt_ctx.variableAssignment()
            target_ctx = var_ctx.assignmentTarget()
            var_name = target_ctx.getText()
            expr = self.visit(var_ctx.expression())

            # Check for self.field = ... assignment (track self write)
            if target_ctx.memberAccess():
                member_ctx = target_ctx.memberAccess()
                # Visit the target to get the expression
                target_expr = self.visit(member_ctx.expression())
                if isinstance(target_expr, SelfExpr) and self._current_struct_method:
                    self._struct_method_self_usage[self._current_struct_method].add("write")
                    # Create an assignment to self.field
                    field_name = member_ctx.IDENTIFIER().getText()
                    return VariableAssignment(
                        variable_name=f"self.{field_name}",
                        value=expr,
                        kind=AssignmentKind.REASSIGNMENT,
                        needs_mut=False,
                    )

            # Handle channel creation
            if isinstance(expr, ChannelCreateExpr):
                channel_info = expr.channel_info or ChannelTypeInfo()

                # Track channel variable
                self._channel_vars[var_name] = channel_info
                self._channel_usages[var_name] = set()

                # Define in scope so lookups know this is a channel
                self._scope.define(var_name, TypeInfo(BaseType.CHANNEL))

                # Determine sender/receiver names
                sender_name = f"{var_name}_tx"
                receiver_name = f"{var_name}_rx"

                # Track the name mapping for later rewriting
                self._channel_name_map[var_name] = (sender_name, receiver_name)

                return ChannelDeclaration(
                    base_name=var_name,
                    sender_name=sender_name,
                    receiver_name=receiver_name,
                    is_bounded=channel_info.is_bounded,
                    capacity=expr.capacity,
                    channel_info=channel_info,
                )

            # Handle array literal assignment
            if isinstance(expr, ArrayLiteralExpr):
                array_info = expr.array_info or ArrayTypeInfo()
                self._array_vars[var_name] = array_info
                self._scope.define(var_name, TypeInfo(BaseType.ARRAY))

                stmt = VariableAssignment(
                    variable_name=var_name,
                    value=expr,
                    kind=AssignmentKind.DECLARATION,
                    needs_mut=False,  # Will be updated if .push() is called
                )
                # Track for later mut fixup when .push() is detected
                self._array_assignments[var_name] = stmt
                return stmt

            # Track struct instance variables for mutability analysis
            struct_name = None
            if isinstance(expr, StructInstantiationExpr):
                struct_name = expr.struct_name
            elif isinstance(expr, StaticMethodCallExpr):
                # e.g., counter = Counter.new(...)
                struct_decl = self._struct_definitions.get(expr.struct_name)
                if struct_decl:
                    # Check if the method returns Self
                    method = next((m for m in struct_decl.methods if m.name == expr.method_name), None)
                    if method and method.return_type == "Self":
                        struct_name = expr.struct_name

            if struct_name:
                self._struct_instance_vars[var_name] = struct_name
                # Check if already tracked for mut method calls
                needs_mut = var_name in self._struct_mut_method_vars

                stmt = VariableAssignment(
                    variable_name=var_name,
                    value=expr,
                    kind=AssignmentKind.DECLARATION,
                    needs_mut=needs_mut,
                )
                # Track for later mut fixup when &mut self method is called
                self._array_assignments[var_name] = stmt  # Reuse array tracking dict
                return stmt

            if isinstance(expr, Expression):
                value = expr
                if expr.type_info:
                    value_type = expr.type_info.base
                else:
                    value_type = BaseType.UNKNOWN
            else:
                value = var_ctx.expression().getText()
                try:
                    value_type = parse_literal(value)
                except ValueError:
                    value_type = BaseType.UNKNOWN

            # For statements inside blocks, we create the assignment directly
            # (no need for two-pass mutability analysis in nested blocks for now)
            return VariableAssignment(
                variable_name=var_name,
                value=value,
                kind=AssignmentKind.DECLARATION,
                needs_mut=False,
            )

        # Check for return statement
        if stmt_ctx.returnStatement():
            ret_ctx = stmt_ctx.returnStatement()
            value = None
            if ret_ctx.expression():
                value = self.visit(ret_ctx.expression())
            return ReturnStatement(value=value)

        # Check for expression statement (includes function calls like print)
        if stmt_ctx.expressionStatement():
            expr_stmt_ctx = stmt_ctx.expressionStatement()
            expr_ctx = expr_stmt_ctx.expression()

            # Check if it's a function call
            if hasattr(expr_ctx, "getRuleIndex"):
                expr_text = expr_ctx.getText()
                # Handle print() calls specially
                if expr_text.startswith("print("):
                    arguments = []
                    func_call_ctx = expr_ctx
                    if hasattr(func_call_ctx, "argumentList") and func_call_ctx.argumentList():
                        for arg_expr in func_call_ctx.argumentList().expression():
                            arguments.append(arg_expr.getText())
                    return PrintStatement(arguments=arguments)

                # Handle other function calls
                expr = self.visit(expr_ctx)
                if isinstance(expr, CallExpr):
                    from zinc.ast.statements import ExpressionStatement
                    return ExpressionStatement(expression=expr)

                # Handle method calls (like b.push(10))
                if isinstance(expr, MethodCallExpr):
                    return MethodCallStatement(
                        target=expr.target,
                        method_name=expr.method_name,
                        arguments=expr.arguments,
                    )

            # Generic expression - just get text for now
            return None

        # Check for nested if statement
        if stmt_ctx.ifStatement():
            if_ctx = stmt_ctx.ifStatement()
            branches = []
            else_body = None

            expressions = if_ctx.expression()
            blocks = if_ctx.block()

            for i in range(len(expressions)):
                condition = self.visit(expressions[i])
                body_stmts = self._visit_block(blocks[i])
                branches.append(IfBranch(condition=condition, body=body_stmts))

            if len(blocks) > len(expressions):
                else_body = self._visit_block(blocks[-1])

            return IfStatement(branches=branches, else_body=else_body)

        # Check for for statement
        if stmt_ctx.forStatement():
            for_ctx = stmt_ctx.forStatement()
            loop_var = for_ctx.IDENTIFIER().getText()
            iterable = self.visit(for_ctx.expression())

            # Enter scope for loop variable
            self._scope = self._scope.enter_scope()

            # Infer loop variable type from iterable
            loop_var_type = TypeInfo(BaseType.UNKNOWN)
            if isinstance(iterable, IdentifierExpr) and iterable.name in self._array_vars:
                array_info = self._array_vars[iterable.name]
                loop_var_type = TypeInfo(array_info.element_type)
            elif isinstance(iterable, RangeExpr):
                loop_var_type = TypeInfo(BaseType.INTEGER)

            self._scope.define(loop_var, loop_var_type)
            body_stmts = self._visit_block(for_ctx.block())
            self._scope = self._scope.exit_scope()

            return ForStatement(
                loop_variable=loop_var,
                iterable=iterable,
                body=body_stmts,
            )

        # Check for spawn statement
        if stmt_ctx.spawnStatement():
            spawn_ctx = stmt_ctx.spawnStatement()
            self._uses_spawn = True

            # Get the function name being called
            func_name = spawn_ctx.expression().getText()

            # Build the arguments list, rewriting channel args to use sender name
            arguments = []
            if spawn_ctx.argumentList():
                for arg_expr in spawn_ctx.argumentList().expression():
                    arg = self.visit(arg_expr)
                    # Rewrite channel arguments to use sender name
                    if isinstance(arg, IdentifierExpr) and arg.name in self._channel_name_map:
                        sender_name, _ = self._channel_name_map[arg.name]
                        arg = IdentifierExpr(name=sender_name, type_info=arg.type_info)
                    arguments.append(arg)

            # Get the callee expression (function name)
            callee = self.visit(spawn_ctx.expression())

            # Create the call expression
            call_expr = CallExpr(callee=callee, arguments=arguments)

            # Extract argument types for monomorphization
            arg_types: list[BaseType] = []
            for arg in arguments:
                if isinstance(arg, Expression) and arg.type_info:
                    arg_types.append(arg.type_info.base)
                else:
                    arg_types.append(BaseType.UNKNOWN)

            # Record call site for monomorphization
            call_site = CallSite(
                func_name=func_name,
                arg_types=tuple(arg_types),
                call_expr=call_expr,
            )
            self._call_sites.append(call_site)

            # Mark that this function is spawned
            type_suffix = "_".join(type_to_rust(t) for t in arg_types)
            mangled_name = f"{func_name}_{type_suffix}"
            self._spawned_functions.add(mangled_name)

            return SpawnStatement(call_expr=call_expr)

        # Check for channel send statement
        if stmt_ctx.channelSendStatement():
            send_ctx = stmt_ctx.channelSendStatement()
            channel_name = send_ctx.IDENTIFIER().getText()
            value_expr = self.visit(send_ctx.expression())

            # Track that this channel is used as a sender
            if channel_name not in self._channel_usages:
                self._channel_usages[channel_name] = set()
            self._channel_usages[channel_name].add("sender")

            # Infer element type from the value being sent
            if channel_name in self._channel_vars:
                chan_info = self._channel_vars[channel_name]
                if chan_info.element_type == BaseType.UNKNOWN:
                    if isinstance(value_expr, Expression) and value_expr.type_info:
                        chan_info.element_type = value_expr.type_info.base

            return ChannelSendStatement(channel_name=channel_name, value=value_expr)

        return None

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

        # Mark arrays with .push() calls as needing mut
        for var_name in self._array_push_vars:
            if var_name in var_state:
                _, decl_index = var_state[var_name]
                needs_mut.add(decl_index)

        # Mark struct instances with &mut self method calls as needing mut
        for var_name in self._struct_mut_method_vars:
            if var_name in var_state:
                _, decl_index = var_state[var_name]
                needs_mut.add(decl_index)

        # Build the final statements list
        # Create a dict of index -> Statement for assignments
        assignment_statements: dict[int, Statement] = {}

        for raw, kind in assignment_info:
            # Update ArrayLiteralExpr with current array info (may have been modified by .push())
            if isinstance(raw.value, ArrayLiteralExpr) and raw.var_name in self._array_vars:
                raw.value.array_info = self._array_vars[raw.var_name]

            stmt = VariableAssignment(
                variable_name=raw.var_name,
                value=raw.value,
                kind=kind,
                needs_mut=(raw.stmt_index in needs_mut),
            )
            assignment_statements[raw.stmt_index] = stmt

        # Process channel declarations - infer element types and generate names
        channel_statements: dict[int, Statement] = {}
        for raw_chan in self._pending_channel_decls:
            var_name = raw_chan.var_name
            chan_info = raw_chan.channel_info
            usages = self._channel_usages.get(var_name, set())

            # Determine sender/receiver names based on usage
            if usages == {"sender"}:
                sender_name = var_name
                receiver_name = f"{var_name}_rx"
            elif usages == {"receiver"}:
                sender_name = f"{var_name}_tx"
                receiver_name = var_name
            else:
                # Both or unknown - use explicit naming
                sender_name = f"{var_name}_tx"
                receiver_name = f"{var_name}_rx"

            stmt = ChannelDeclaration(
                base_name=var_name,
                sender_name=sender_name,
                receiver_name=receiver_name,
                is_bounded=chan_info.is_bounded,
                capacity=None,  # TODO: Store capacity expression if bounded
                channel_info=chan_info,
            )
            channel_statements[raw_chan.stmt_index] = stmt

        # Merge assignments, channels, and other statements in order
        all_statements: dict[int, Statement] = {}
        all_statements.update(assignment_statements)
        all_statements.update(channel_statements)
        for idx, stmt in self._pending_other:
            all_statements[idx] = stmt

        # Sort by index and populate self.statements
        self.statements = [all_statements[i] for i in sorted(all_statements.keys())]

    # ============================================================
    # Pass 3: Monomorphization
    # ============================================================

    def monomorphize(self) -> None:
        """
        Generate specialized function variants based on call site types.

        For each unique (func_name, arg_types) combination:
        1. Create a mangled function name
        2. Clone the function template with resolved parameter types
        3. Infer return type from the function body
        4. Update call expressions to use the mangled name
        """
        import copy

        # Group call sites by (func_name, arg_types) to find unique signatures
        signatures: dict[tuple[str, tuple[BaseType, ...]], list[CallSite]] = {}
        for call_site in self._call_sites:
            key = (call_site.func_name, call_site.arg_types)
            if key not in signatures:
                signatures[key] = []
            signatures[key].append(call_site)

        # Generate monomorphized functions for each unique signature
        for (func_name, arg_types), call_sites in signatures.items():
            # Skip if not a template function (might be a builtin or already typed)
            if func_name not in self._function_templates:
                continue

            template = self._function_templates[func_name]

            # Generate mangled name: add_i64_i64
            type_suffix = "_".join(type_to_rust(t) for t in arg_types)
            mangled_name = f"{func_name}_{type_suffix}"

            # Clone the template and set resolved types
            mono_func = copy.deepcopy(template)
            mono_func.name = func_name  # Keep original name for reference
            mono_func.mangled_name = mangled_name
            mono_func.is_template = False

            # Analyze function body to determine channel parameter usage
            channel_param_roles = self._analyze_channel_params(mono_func.body, template.parameters)

            # Build param index map for type lookup
            param_index = {p.name: i for i, p in enumerate(template.parameters)}

            # Set resolved types on parameters
            for i, param in enumerate(mono_func.parameters):
                if i < len(arg_types):
                    if arg_types[i] == BaseType.CHANNEL:
                        # This is a channel parameter - determine if sender or receiver
                        role_info = channel_param_roles.get(param.name, ("sender", None, BaseType.UNKNOWN))
                        role, source_param, inferred_elem_type = role_info

                        # Infer element type from the source parameter
                        elem_type = BaseType.UNKNOWN
                        if source_param and source_param in param_index:
                            source_idx = param_index[source_param]
                            if source_idx < len(arg_types):
                                elem_type = arg_types[source_idx]

                        # Use inferred type from literals if available
                        if elem_type == BaseType.UNKNOWN and inferred_elem_type != BaseType.UNKNOWN:
                            elem_type = inferred_elem_type

                        # Fall back to channel variable lookup
                        if elem_type == BaseType.UNKNOWN:
                            elem_type = self._get_channel_element_type(param.name, call_sites)

                        # Update the channel variable's element type
                        self._update_channel_element_types(call_sites, i, elem_type)

                        # Look up is_bounded from the original channel variable
                        is_bounded = self._get_channel_is_bounded(call_sites, i)

                        chan_info = ChannelTypeInfo(element_type=elem_type, is_bounded=is_bounded)
                        if role == "sender":
                            param.resolved_type = chan_info.to_rust_sender()
                        else:
                            param.resolved_type = chan_info.to_rust_receiver()
                    else:
                        param.resolved_type = type_to_rust(arg_types[i])

            # Update is_bounded on ChannelSendStatement objects in the function body
            # Build mapping of param name -> is_bounded
            param_is_bounded: dict[str, bool] = {}
            for i, param in enumerate(mono_func.parameters):
                if i < len(arg_types) and arg_types[i] == BaseType.CHANNEL:
                    param_is_bounded[param.name] = self._get_channel_is_bounded(call_sites, i)
            self._update_send_statements_bounded(mono_func.body, param_is_bounded)

            # Infer return type from the function body
            return_type = self._infer_return_type(mono_func.body, arg_types, template.parameters)
            if return_type != BaseType.UNKNOWN:
                mono_func.return_type = type_to_rust(return_type)

            # Mark as async if this function is spawned
            if mangled_name in self._spawned_functions:
                mono_func.is_async = True

            self._monomorphized.append(mono_func)

            # Update all call expressions for this signature to use mangled name
            for call_site in call_sites:
                call_site.call_expr.mangled_name = mangled_name
                # Set the return type on the call expression
                if return_type != BaseType.UNKNOWN:
                    call_site.call_expr.type_info = TypeInfo(return_type)

    def _infer_return_type(
        self,
        body: list[Statement],
        arg_types: tuple[BaseType, ...],
        params: list[Parameter],
    ) -> BaseType:
        """Infer the return type of a function from its body."""
        # Build a mapping of parameter name -> type
        param_types: dict[str, BaseType] = {}
        for i, param in enumerate(params):
            if i < len(arg_types):
                param_types[param.name] = arg_types[i]

        # Look for return statements and infer their types
        for stmt in body:
            if isinstance(stmt, ReturnStatement) and stmt.value:
                return self._infer_expr_type(stmt.value, param_types)

        return BaseType.UNKNOWN

    def _infer_expr_type(self, expr: Expression, param_types: dict[str, BaseType]) -> BaseType:
        """Infer the type of an expression given parameter type mappings."""
        if expr.type_info and expr.type_info.base != BaseType.UNKNOWN:
            return expr.type_info.base

        if isinstance(expr, IdentifierExpr):
            # Look up in parameter types
            if expr.name in param_types:
                return param_types[expr.name]

        if isinstance(expr, BinaryExpr):
            left_type = self._infer_expr_type(expr.left, param_types)
            right_type = self._infer_expr_type(expr.right, param_types)
            # Use type promotion rules
            result = TypeInfo.promote(TypeInfo(left_type), TypeInfo(right_type))
            return result.base

        if isinstance(expr, ParenExpr):
            return self._infer_expr_type(expr.inner, param_types)

        return BaseType.UNKNOWN

    def _analyze_channel_params(
        self, body: list[Statement], params: list[Parameter]
    ) -> dict[str, tuple[str, str | None, BaseType]]:
        """Analyze function body to determine if channel params are senders or receivers.

        Returns a dict of param_name -> (role, source_param_name, inferred_elem_type).
        - role is "sender" or "receiver"
        - source_param_name is the param whose value is sent (for type inference)
        - inferred_elem_type is the type inferred from literals being sent
        """
        param_names = {p.name for p in params}
        roles: dict[str, tuple[str, str | None, BaseType]] = {}

        def visit_stmt(stmt: Statement) -> None:
            if isinstance(stmt, ChannelSendStatement):
                # sender <- value : channel_name is a sender
                if stmt.channel_name in param_names:
                    # Check if the value being sent is another parameter
                    source_param = None
                    inferred_type = BaseType.UNKNOWN
                    if isinstance(stmt.value, IdentifierExpr):
                        if stmt.value.name in param_names:
                            source_param = stmt.value.name
                    # Also check if the value has a known type (e.g., literal)
                    if isinstance(stmt.value, Expression) and stmt.value.type_info:
                        inferred_type = stmt.value.type_info.base
                    roles[stmt.channel_name] = ("sender", source_param, inferred_type)
            elif isinstance(stmt, VariableAssignment):
                # x = <- channel : check if value is a receive expression
                if isinstance(stmt.value, ChannelReceiveExpr):
                    if isinstance(stmt.value.channel, IdentifierExpr):
                        if stmt.value.channel.name in param_names:
                            roles[stmt.value.channel.name] = ("receiver", None, BaseType.UNKNOWN)
            elif isinstance(stmt, IfStatement):
                for branch in stmt.branches:
                    for s in branch.body:
                        visit_stmt(s)
                if stmt.else_body:
                    for s in stmt.else_body:
                        visit_stmt(s)

        for stmt in body:
            visit_stmt(stmt)

        return roles

    def _get_channel_element_type(
        self, param_name: str, call_sites: list[CallSite]
    ) -> BaseType:
        """Get the element type of a channel passed to a function.

        Looks up the channel variable passed at call sites and returns its element type.
        """
        for call_site in call_sites:
            for arg in call_site.call_expr.arguments:
                if isinstance(arg, IdentifierExpr):
                    # Check if this arg is a channel variable we know about
                    if arg.name in self._channel_vars:
                        chan_info = self._channel_vars[arg.name]
                        return chan_info.element_type
        return BaseType.UNKNOWN

    def _update_channel_element_types(
        self, call_sites: list[CallSite], param_idx: int, elem_type: BaseType
    ) -> None:
        """Update channel variable element types based on inferred type.

        When we determine a channel's element type during monomorphization,
        update the channel variable so declarations render correctly.
        """
        if elem_type == BaseType.UNKNOWN:
            return

        # Build reverse mapping: tx/rx name -> original channel name
        reverse_map: dict[str, str] = {}
        for orig_name, (tx_name, rx_name) in self._channel_name_map.items():
            reverse_map[tx_name] = orig_name
            reverse_map[rx_name] = orig_name

        for call_site in call_sites:
            if param_idx < len(call_site.call_expr.arguments):
                arg = call_site.call_expr.arguments[param_idx]
                if isinstance(arg, IdentifierExpr):
                    # Check if it's a rewritten name
                    orig_name = reverse_map.get(arg.name, arg.name)
                    if orig_name in self._channel_vars:
                        self._channel_vars[orig_name].element_type = elem_type

    def _get_channel_is_bounded(
        self, call_sites: list[CallSite], param_idx: int
    ) -> bool:
        """Get whether a channel passed to a function is bounded.

        Looks up the channel variable passed at call sites and returns its is_bounded property.
        """
        # Build reverse mapping: tx/rx name -> original channel name
        reverse_map: dict[str, str] = {}
        for orig_name, (tx_name, rx_name) in self._channel_name_map.items():
            reverse_map[tx_name] = orig_name
            reverse_map[rx_name] = orig_name

        for call_site in call_sites:
            if param_idx < len(call_site.call_expr.arguments):
                arg = call_site.call_expr.arguments[param_idx]
                if isinstance(arg, IdentifierExpr):
                    # Check if it's a rewritten name
                    orig_name = reverse_map.get(arg.name, arg.name)
                    if orig_name in self._channel_vars:
                        return self._channel_vars[orig_name].is_bounded
        return False

    def _update_send_statements_bounded(
        self, body: list[Statement], param_is_bounded: dict[str, bool]
    ) -> None:
        """Update is_bounded on ChannelSendStatement objects in a function body.

        Recursively visits statements and sets is_bounded based on the param mapping.
        """
        for stmt in body:
            if isinstance(stmt, ChannelSendStatement):
                stmt.is_bounded = param_is_bounded.get(stmt.channel_name, False)
            elif isinstance(stmt, IfStatement):
                # Recursively process if branches
                for branch in stmt.branches:
                    self._update_send_statements_bounded(branch.body, param_is_bounded)
                if stmt.else_body:
                    self._update_send_statements_bounded(stmt.else_body, param_is_bounded)
