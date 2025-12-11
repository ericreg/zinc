"""Visitor for the Zinc compiler - transforms parse tree to AST and generates code."""

from dataclasses import dataclass
from typing import Union

from zinc.parser.zincParser import zincParser as ZincParser
from zinc.parser.zincVisitor import zincVisitor as ZincVisitor

from zinc.ast.types import BaseType, TypeInfo, parse_literal, type_to_rust
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
    IfBranch,
    IfStatement,
    Parameter,
    FunctionDeclaration,
    ReturnStatement,
    SpawnStatement,
)
from zinc.ast.expressions import CallExpr
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


class Program:
    """Represents a compiled Zinc program."""

    def __init__(
        self,
        scope: Scope,
        statements: list[Statement],
        monomorphized: list[Statement] | None = None,
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

    def visitFunctionCallExpr(self, ctx: ZincParser.FunctionCallExprContext) -> Expression | None:
        """Visit function call expression."""
        # Get the callee expression
        callee = self.visit(ctx.expression())
        func_name = ctx.expression().getText()

        # Get the arguments as Expression AST nodes
        arguments = []
        if ctx.argumentList():
            for arg_expr in ctx.argumentList().expression():
                arguments.append(self.visit(arg_expr))

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

    def _visit_block(self, block_ctx) -> list[Statement]:
        """Visit a block and return list of statements."""
        statements = []

        for stmt_ctx in block_ctx.statement():
            # Handle each statement type
            stmt = self._visit_statement(stmt_ctx)
            if stmt:
                statements.append(stmt)

        return statements

    def _visit_statement(self, stmt_ctx) -> Statement | None:
        """Visit a single statement and return a Statement object."""
        # Check for variable assignment
        if stmt_ctx.variableAssignment():
            var_ctx = stmt_ctx.variableAssignment()
            var_name = var_ctx.assignmentTarget().getText()
            expr = self.visit(var_ctx.expression())

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

        # Check for spawn statement
        if stmt_ctx.spawnStatement():
            spawn_ctx = stmt_ctx.spawnStatement()
            self._uses_spawn = True

            # Get the function name being called
            func_name = spawn_ctx.expression().getText()

            # Build the arguments list
            arguments = []
            if spawn_ctx.argumentList():
                for arg_expr in spawn_ctx.argumentList().expression():
                    arguments.append(self.visit(arg_expr))

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

            # Set resolved types on parameters
            for i, param in enumerate(mono_func.parameters):
                if i < len(arg_types):
                    param.resolved_type = type_to_rust(arg_types[i])

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
