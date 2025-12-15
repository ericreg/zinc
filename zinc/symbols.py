"""Symbol Table for the Zinc compiler."""

from dataclasses import dataclass
from enum import Enum, auto

from antlr4 import ParserRuleContext

from zinc.ast.types import BaseType, TypeInfo, parse_literal, is_mutating_method, type_to_rust, ChannelTypeInfo
from zinc.parser.zincVisitor import zincVisitor
from zinc.parser.zincParser import zincParser as ZincParser
from zinc.atlas import Atlas, FunctionInstance, ConstInstance


class SymbolKind(Enum):
    """Kind of symbol in the symbol table."""

    VARIABLE = auto()  # Local variable
    PARAMETER = auto()  # Function parameter
    CONST = auto()  # Global constant
    TEMPORARY = auto()  # Intermediate expression result
    FUNCTION = auto()  # User-defined function
    BUILTIN = auto()  # Built-in function (print, chan, etc.)
    STRUCT = auto()  # Struct type
    LITERAL = auto()  # Literal value


@dataclass
class Symbol:
    """A symbol in the symbol table."""

    id: str | None  # Original name (None for temporaries/literals)
    unique_name: str  # Scoped unique name with type (e.g., "main.a/i64", "tmp_0")
    kind: SymbolKind
    resolved_type: BaseType
    source_interval: tuple[int, int]  # ANTLR source interval (start, stop)
    is_mutated: bool = False  # True if variable needs 'mut' (reassigned or mutating method called)
    is_shadow: bool = False  # True if this shadows a previous binding of the same name


class SymbolTable:
    """Scoped symbol table with lookup by id or source interval."""

    def __init__(self):
        self._symbols: list[Symbol] = []
        self._by_interval: dict[str, Symbol] = {}  # "(start, stop)" -> Symbol
        self._scope_stack: list[dict[str, Symbol]] = [{}]  # Stack of id -> Symbol
        self._temp_counter: int = 0
        self._scope_path: list[str] = []  # e.g., ["main", "if_0"]

    @property
    def current_scope(self) -> str:
        """Return current scope path like 'main.if_0'."""
        return ".".join(self._scope_path) if self._scope_path else "global"

    def enter_scope(self, name: str) -> None:
        """Enter a new scope (function, if block, for loop, etc.)."""
        self._scope_path.append(name)
        self._scope_stack.append({})

    def exit_scope(self) -> None:
        """Exit current scope."""
        self._scope_path.pop()
        self._scope_stack.pop()

    def define(
        self,
        id: str,
        kind: SymbolKind,
        resolved_type: BaseType,
        interval: tuple[int, int],
        is_shadow: bool = False,
    ) -> Symbol:
        """Define a named symbol in current scope."""
        # Include type in unique_name for shadowing support
        type_suffix = type_to_rust(resolved_type)
        base_name = f"{self.current_scope}.{id}" if self._scope_path else id
        unique_name = f"{base_name}/{type_suffix}"

        symbol = Symbol(
            id=id,
            unique_name=unique_name,
            kind=kind,
            resolved_type=resolved_type,
            source_interval=interval,
            is_shadow=is_shadow,
        )
        self._symbols.append(symbol)
        self._by_interval[f"({interval[0]}, {interval[1]})"] = symbol
        # Always update scope - this handles shadowing within same scope
        self._scope_stack[-1][id] = symbol
        return symbol

    def define_temp(
        self,
        resolved_type: BaseType,
        interval: tuple[int, int],
        kind: SymbolKind = SymbolKind.TEMPORARY,
    ) -> Symbol:
        """Define a temporary symbol for an expression."""
        unique_name = f"tmp_{self._temp_counter}"
        self._temp_counter += 1
        symbol = Symbol(
            id=None,
            unique_name=unique_name,
            kind=kind,
            resolved_type=resolved_type,
            source_interval=interval,
        )
        self._symbols.append(symbol)
        self._by_interval[f"({interval[0]}, {interval[1]})"] = symbol
        return symbol

    def lookup_by_id(self, id: str) -> Symbol | None:
        """Look up symbol by name in current and enclosing scopes."""
        for scope in reversed(self._scope_stack):
            if id in scope:
                return scope[id]
        return None

    def lookup_by_interval(self, interval: tuple[int, int]) -> Symbol | None:
        """Look up symbol by source interval."""
        key = f"({interval[0]}, {interval[1]})"
        return self._by_interval.get(key)

    def all_symbols(self) -> list[Symbol]:
        """Return all defined symbols."""
        return self._symbols.copy()


class SymbolTableVisitor(zincVisitor):
    """Walks reachable code and builds a SymbolTable."""

    def __init__(self, atlas: Atlas):
        self.atlas = atlas
        self.symbols = SymbolTable()
        self._block_counters: dict[str, int] = {}  # For unique block names
        self._current_function: str | None = None
        self._current_return_type: BaseType = BaseType.VOID  # Track return type during resolution
        # Maps call site interval -> mangled name for CodeGen to use
        self.specialization_map: dict[tuple[int, int], str] = {}
        # Track channel variables and their type info (var_name -> ChannelTypeInfo)
        self._channel_infos: dict[str, ChannelTypeInfo] = {}

    def resolve(self) -> SymbolTable:
        """Main entry point - resolve types for all reachable code.

        Processes functions in reverse topological order (callers before callees).
        When a call site is visited, creates a specialization in the Atlas with
        concrete argument types. Then processes each specialization.
        """
        self._register_builtins()

        for const in self.atlas.consts.values():
            self._resolve_const(const)

        # Process in reverse topological order (callers before callees)
        # This ensures we see call sites and create specializations before
        # processing the callee function
        order = list(reversed(self.atlas.topological_order()))
        processed: set[str] = set()

        # Keep processing until no new specializations are added
        while True:
            new_work = False
            # Get current list of functions (may grow as we discover specializations)
            current_functions = list(self.atlas.functions.keys())
            for mangled_name in current_functions:
                if mangled_name in processed:
                    continue
                processed.add(mangled_name)
                new_work = True
                func = self.atlas.functions[mangled_name]
                self._resolve_function(func)

            if not new_work:
                break

        return self.symbols

    def _register_builtins(self) -> None:
        """Register built-in functions."""
        self.symbols.define(
            id="print",
            kind=SymbolKind.BUILTIN,
            resolved_type=BaseType.VOID,
            interval=(-1, -1),
        )
        self.symbols.define(
            id="chan",
            kind=SymbolKind.BUILTIN,
            resolved_type=BaseType.CHANNEL,
            interval=(-1, -1),
        )

    def _next_block_name(self, prefix: str) -> str:
        """Generate unique block name like 'if_0', 'for_1'."""
        count = self._block_counters.get(prefix, 0)
        self._block_counters[prefix] = count + 1
        return f"{prefix}_{count}"

    def _resolve_const(self, const: ConstInstance) -> None:
        """Resolve type of a global constant."""
        ctx: ZincParser.ConstDeclarationContext = const.ctx  # type: ignore[assignment]
        expr_type = self.visit(ctx.expression())
        self.symbols.define(
            id=const.name,
            kind=SymbolKind.CONST,
            resolved_type=expr_type,
            interval=ctx.getSourceInterval(),
        )

    def _resolve_function(self, func: FunctionInstance) -> None:
        """Resolve types within a function body for a specific specialization."""
        self._block_counters.clear()
        self._current_function = func.mangled_name
        self._current_return_type = BaseType.VOID  # Reset for this function

        # Use mangled name for scope so symbols are per-specialization
        self.symbols.enter_scope(func.mangled_name)

        # Define parameters with types from func.arg_types
        ctx = func.ctx
        if hasattr(ctx, "parameterList") and ctx.parameterList():
            for i, param_ctx in enumerate(ctx.parameterList().parameter()):
                param_name = param_ctx.IDENTIFIER().getText()
                # Use arg type from specialization if available
                if i < len(func.arg_types):
                    param_type = func.arg_types[i]
                else:
                    param_type = BaseType.UNKNOWN
                self.symbols.define(
                    id=param_name,
                    kind=SymbolKind.PARAMETER,
                    resolved_type=param_type,
                    interval=param_ctx.getSourceInterval(),
                )
                # Track channel parameters for element type inference
                if param_type == BaseType.CHANNEL and i in func.arg_channel_infos:
                    self._channel_infos[param_name] = func.arg_channel_infos[i]

        # Visit function body (skip parameter list since we handled it)
        if hasattr(ctx, "block"):
            self.visit(ctx.block())

        # Store the inferred return type
        func.return_type = self._current_return_type

        self.symbols.exit_scope()
        self._current_function = None

    def visitLiteral(self, ctx: ZincParser.LiteralContext) -> BaseType:
        """Visit a literal and create a symbol for it."""
        text = ctx.getText()
        base_type = parse_literal(text)
        self.symbols.define_temp(
            resolved_type=base_type,
            interval=ctx.getSourceInterval(),
            kind=SymbolKind.LITERAL,
        )
        return base_type

    def visitPrimaryExpression(self, ctx: ZincParser.PrimaryExpressionContext) -> BaseType:
        """Handle primary expressions (literals, identifiers, etc.)."""
        if ctx.literal():
            return self.visit(ctx.literal())

        if ctx.IDENTIFIER():
            name = ctx.IDENTIFIER().getText()
            symbol = self.symbols.lookup_by_id(name)
            if symbol:
                self.symbols.define_temp(
                    resolved_type=symbol.resolved_type,
                    interval=ctx.getSourceInterval(),
                )
                return symbol.resolved_type
            self.symbols.define_temp(
                resolved_type=BaseType.UNKNOWN,
                interval=ctx.getSourceInterval(),
            )
            return BaseType.UNKNOWN

        if ctx.arrayLiteral():
            return self.visit(ctx.arrayLiteral())

        if ctx.structInstantiation():
            return self.visit(ctx.structInstantiation())

        if ctx.getText() == "self":
            self.symbols.define_temp(
                resolved_type=BaseType.STRUCT,
                interval=ctx.getSourceInterval(),
            )
            return BaseType.STRUCT

        self.symbols.define_temp(
            resolved_type=BaseType.UNKNOWN,
            interval=ctx.getSourceInterval(),
        )
        return BaseType.UNKNOWN

    def visitPrimaryExpr(self, ctx: ZincParser.PrimaryExprContext) -> BaseType:
        """Visit primary expression wrapper."""
        return self.visit(ctx.primaryExpression())

    def visitParenExpr(self, ctx: ZincParser.ParenExprContext) -> BaseType:
        """Handle parenthesized expressions."""
        inner_type = self.visit(ctx.expression())
        self.symbols.define_temp(
            resolved_type=inner_type,
            interval=ctx.getSourceInterval(),
        )
        return inner_type

    def visitAdditiveExpr(self, ctx: ZincParser.AdditiveExprContext) -> BaseType:
        """Handle addition and subtraction."""
        left_type = self.visit(ctx.expression(0))
        right_type = self.visit(ctx.expression(1))
        result_type = TypeInfo.promote(TypeInfo(left_type), TypeInfo(right_type)).base
        self.symbols.define_temp(
            resolved_type=result_type,
            interval=ctx.getSourceInterval(),
        )
        return result_type

    def visitMultiplicativeExpr(self, ctx: ZincParser.MultiplicativeExprContext) -> BaseType:
        """Handle multiplication, division, modulo."""
        left_type = self.visit(ctx.expression(0))
        right_type = self.visit(ctx.expression(1))
        result_type = TypeInfo.promote(TypeInfo(left_type), TypeInfo(right_type)).base
        self.symbols.define_temp(
            resolved_type=result_type,
            interval=ctx.getSourceInterval(),
        )
        return result_type

    def visitUnaryExpr(self, ctx: ZincParser.UnaryExprContext) -> BaseType:
        """Handle unary expressions."""
        operand_type = self.visit(ctx.expression())
        operator = ctx.getChild(0).getText()

        if operator == "-":
            result_type = operand_type
        else:
            result_type = BaseType.BOOLEAN

        self.symbols.define_temp(
            resolved_type=result_type,
            interval=ctx.getSourceInterval(),
        )
        return result_type

    def visitRelationalExpr(self, ctx: ZincParser.RelationalExprContext) -> BaseType:
        """Handle relational comparisons."""
        self.visit(ctx.expression(0))
        self.visit(ctx.expression(1))
        self.symbols.define_temp(
            resolved_type=BaseType.BOOLEAN,
            interval=ctx.getSourceInterval(),
        )
        return BaseType.BOOLEAN

    def visitEqualityExpr(self, ctx: ZincParser.EqualityExprContext) -> BaseType:
        """Handle equality comparisons."""
        self.visit(ctx.expression(0))
        self.visit(ctx.expression(1))
        self.symbols.define_temp(
            resolved_type=BaseType.BOOLEAN,
            interval=ctx.getSourceInterval(),
        )
        return BaseType.BOOLEAN

    def visitLogicalAndExpr(self, ctx: ZincParser.LogicalAndExprContext) -> BaseType:
        """Handle logical AND."""
        self.visit(ctx.expression(0))
        self.visit(ctx.expression(1))
        self.symbols.define_temp(
            resolved_type=BaseType.BOOLEAN,
            interval=ctx.getSourceInterval(),
        )
        return BaseType.BOOLEAN

    def visitLogicalOrExpr(self, ctx: ZincParser.LogicalOrExprContext) -> BaseType:
        """Handle logical OR."""
        self.visit(ctx.expression(0))
        self.visit(ctx.expression(1))
        self.symbols.define_temp(
            resolved_type=BaseType.BOOLEAN,
            interval=ctx.getSourceInterval(),
        )
        return BaseType.BOOLEAN

    def visitArrayLiteral(self, ctx: ZincParser.ArrayLiteralContext) -> BaseType:
        """Visit array literal."""
        for expr_ctx in ctx.expression():
            self.visit(expr_ctx)
        self.symbols.define_temp(
            resolved_type=BaseType.ARRAY,
            interval=ctx.getSourceInterval(),
        )
        return BaseType.ARRAY

    def visitIndexAccessExpr(self, ctx: ZincParser.IndexAccessExprContext) -> BaseType:
        """Visit index access."""
        self.visit(ctx.expression(0))
        self.visit(ctx.expression(1))
        self.symbols.define_temp(
            resolved_type=BaseType.UNKNOWN,
            interval=ctx.getSourceInterval(),
        )
        return BaseType.UNKNOWN

    def visitRangeExpr(self, ctx: ZincParser.RangeExprContext) -> BaseType:
        """Visit range expression."""
        self.visit(ctx.expression(0))
        self.visit(ctx.expression(1))
        self.symbols.define_temp(
            resolved_type=BaseType.INTEGER,
            interval=ctx.getSourceInterval(),
        )
        return BaseType.INTEGER

    def visitMemberAccessExpr(self, ctx: ZincParser.MemberAccessExprContext) -> BaseType:
        """Handle member access."""
        self.visit(ctx.expression())
        self.symbols.define_temp(
            resolved_type=BaseType.UNKNOWN,
            interval=ctx.getSourceInterval(),
        )
        return BaseType.UNKNOWN

    def visitFunctionCallExpr(self, ctx: ZincParser.FunctionCallExprContext) -> BaseType:
        """Visit function call expression and create specialization if needed."""
        self.visit(ctx.expression())

        # Collect argument types
        arg_types: list[BaseType] = []
        if ctx.argumentList():
            for arg_expr in ctx.argumentList().expression():
                arg_type = self.visit(arg_expr)
                arg_types.append(arg_type)

        callee_ctx = ctx.expression()

        # Check for method call (e.g., b.push(10))
        if isinstance(callee_ctx, ZincParser.MemberAccessExprContext):
            method_name = callee_ctx.IDENTIFIER().getText()
            receiver_ctx = callee_ctx.expression()

            # Get the receiver variable name if it's a simple identifier
            if isinstance(receiver_ctx, ZincParser.PrimaryExprContext):
                primary = receiver_ctx.primaryExpression()
                if primary and primary.IDENTIFIER():
                    var_name = primary.IDENTIFIER().getText()
                    var_symbol = self.symbols.lookup_by_id(var_name)
                    if var_symbol:
                        # Check if this method mutates the receiver
                        if is_mutating_method(var_symbol.resolved_type, method_name):
                            var_symbol.is_mutated = True

        # Create specialization for user-defined functions
        if isinstance(callee_ctx, ZincParser.PrimaryExprContext):
            primary = callee_ctx.primaryExpression()
            if primary and primary.IDENTIFIER():
                func_name = primary.IDENTIFIER().getText()
                if func_name not in ("print", "chan"):
                    # Look up function definition
                    func_def = self.atlas.function_defs.get(func_name)
                    if func_def and arg_types:
                        # Create specialization in Atlas (pass caller for call graph)
                        mangled = self.atlas.add_specialization(
                            func_name, arg_types, func_def, self._current_function
                        )
                        # Store mapping from call site to mangled name
                        self.specialization_map[ctx.getSourceInterval()] = mangled

                func_symbol = self.symbols.lookup_by_id(func_name)
                if func_symbol:
                    self.symbols.define_temp(
                        resolved_type=func_symbol.resolved_type,
                        interval=ctx.getSourceInterval(),
                    )
                    return func_symbol.resolved_type

        self.symbols.define_temp(
            resolved_type=BaseType.UNKNOWN,
            interval=ctx.getSourceInterval(),
        )
        return BaseType.UNKNOWN

    def visitStructInstantiation(self, ctx: ZincParser.StructInstantiationContext) -> BaseType:
        """Visit struct literal."""
        for field_ctx in ctx.fieldInit():
            self.visit(field_ctx.expression())
        self.symbols.define_temp(
            resolved_type=BaseType.STRUCT,
            interval=ctx.getSourceInterval(),
        )
        return BaseType.STRUCT

    def visitVariableAssignment(self, ctx: ZincParser.VariableAssignmentContext) -> None:
        """Visit variable assignment with shadowing support."""
        expr_type = self.visit(ctx.expression())
        target = ctx.assignmentTarget()

        if target.IDENTIFIER():
            var_name = target.IDENTIFIER().getText()
            existing = self.symbols.lookup_by_id(var_name)

            # Check if this is a chan() call - track channel info
            if expr_type == BaseType.CHANNEL:
                expr = ctx.expression()
                if isinstance(expr, ZincParser.FunctionCallExprContext):
                    callee = expr.expression()
                    if isinstance(callee, ZincParser.PrimaryExprContext):
                        primary = callee.primaryExpression()
                        if primary and primary.IDENTIFIER() and primary.IDENTIFIER().getText() == "chan":
                            # Create ChannelTypeInfo for this channel variable
                            self._channel_infos[var_name] = ChannelTypeInfo(element_type=BaseType.UNKNOWN)

            if existing is None:
                # First assignment - create new symbol
                self.symbols.define(
                    id=var_name,
                    kind=SymbolKind.VARIABLE,
                    resolved_type=expr_type,
                    interval=target.getSourceInterval(),
                    is_shadow=False,
                )
            elif existing.resolved_type != expr_type:
                # Type change - create shadow symbol
                self.symbols.define(
                    id=var_name,
                    kind=SymbolKind.VARIABLE,
                    resolved_type=expr_type,
                    interval=target.getSourceInterval(),
                    is_shadow=True,
                )
            else:
                # Same type reassignment - mark original as mutated
                existing.is_mutated = True
                # Still create entry in _by_interval for this assignment
                self.symbols.define_temp(
                    resolved_type=expr_type,
                    interval=target.getSourceInterval(),
                )
        else:
            self.symbols.define_temp(
                resolved_type=expr_type,
                interval=target.getSourceInterval(),
            )

    def visitReturnStatement(self, ctx: ZincParser.ReturnStatementContext) -> None:
        """Visit return statement and track return type."""
        if ctx.expression():
            return_type = self.visit(ctx.expression())
            # Track the return type (first return statement wins)
            if self._current_return_type == BaseType.VOID:
                self._current_return_type = return_type

    def visitIfStatement(self, ctx: ZincParser.IfStatementContext) -> None:
        """Visit if/else statement."""
        for expr in ctx.expression():
            self.visit(expr)

        for i, block in enumerate(ctx.block()):
            block_name = self._next_block_name("if")
            self.symbols.enter_scope(block_name)
            self.visit(block)
            self.symbols.exit_scope()

    def visitForStatement(self, ctx: ZincParser.ForStatementContext) -> None:
        """Visit for-in loop statement."""
        iterable_type = self.visit(ctx.expression())

        block_name = self._next_block_name("for")
        self.symbols.enter_scope(block_name)

        loop_var = ctx.IDENTIFIER().getText()
        if iterable_type == BaseType.INTEGER:
            var_type = BaseType.INTEGER
        else:
            var_type = BaseType.UNKNOWN

        self.symbols.define(
            id=loop_var,
            kind=SymbolKind.VARIABLE,
            resolved_type=var_type,
            interval=(ctx.IDENTIFIER().getSourceInterval()),
        )

        self.visit(ctx.block())
        self.symbols.exit_scope()

    def visitWhileStatement(self, ctx: ZincParser.WhileStatementContext) -> None:
        """Visit while loop statement."""
        self.visit(ctx.expression())

        block_name = self._next_block_name("while")
        self.symbols.enter_scope(block_name)
        self.visit(ctx.block())
        self.symbols.exit_scope()

    def visitLoopStatement(self, ctx: ZincParser.LoopStatementContext) -> None:
        """Visit loop statement."""
        block_name = self._next_block_name("loop")
        self.symbols.enter_scope(block_name)
        self.visit(ctx.block())
        self.symbols.exit_scope()

    def visitBlock(self, ctx: ZincParser.BlockContext) -> None:
        """Visit a block of statements."""
        for stmt in ctx.statement():
            self.visit(stmt)

    def visitExpressionStatement(self, ctx: ZincParser.ExpressionStatementContext) -> None:
        """Visit expression statement."""
        self.visit(ctx.expression())

    def visitSpawnStatement(self, ctx: ZincParser.SpawnStatementContext) -> None:
        """Visit spawn statement and create specialization for spawned function."""
        # Grammar: spawn expression '(' argumentList? ')'
        # The expression is the function name
        func_expr = ctx.expression()
        if isinstance(func_expr, ZincParser.PrimaryExprContext):
            primary = func_expr.primaryExpression()
            if primary and primary.IDENTIFIER():
                func_name = primary.IDENTIFIER().getText()

                # Collect argument types and track channel arguments
                arg_types: list[BaseType] = []
                arg_channel_infos: dict[int, ChannelTypeInfo] = {}
                if ctx.argumentList():
                    for i, arg_expr in enumerate(ctx.argumentList().expression()):
                        arg_type = self.visit(arg_expr)
                        arg_types.append(arg_type)

                        # Check if argument is a channel variable
                        if arg_type == BaseType.CHANNEL:
                            if isinstance(arg_expr, ZincParser.PrimaryExprContext):
                                arg_primary = arg_expr.primaryExpression()
                                if arg_primary and arg_primary.IDENTIFIER():
                                    chan_var = arg_primary.IDENTIFIER().getText()
                                    if chan_var in self._channel_infos:
                                        arg_channel_infos[i] = self._channel_infos[chan_var]

                # Create specialization for the spawned function
                if func_name not in ("print", "chan"):
                    func_def = self.atlas.function_defs.get(func_name)
                    if func_def and arg_types:
                        mangled = self.atlas.add_specialization(
                            func_name, arg_types, func_def, self._current_function
                        )
                        # Store mapping from spawn site to mangled name
                        self.specialization_map[ctx.getSourceInterval()] = mangled
                        # Mark the function as async since it's being spawned
                        self.atlas.functions[mangled].is_async = True
                        # Propagate channel type info to the function instance
                        self.atlas.functions[mangled].arg_channel_infos = arg_channel_infos

    def visitChannelSendStatement(self, ctx: ZincParser.ChannelSendStatementContext) -> None:
        """Visit channel send statement and infer channel element type."""
        # Grammar: IDENTIFIER '<-' expression
        channel_name = ctx.IDENTIFIER().getText()
        value_type = self.visit(ctx.expression())

        # Update channel info with inferred element type
        if channel_name in self._channel_infos:
            chan_info = self._channel_infos[channel_name]
            if chan_info.element_type == BaseType.UNKNOWN:
                chan_info.element_type = value_type

    def visitChannelReceiveExpr(self, ctx: ZincParser.ChannelReceiveExprContext) -> BaseType:
        """Visit channel receive expression."""
        # Grammar: '<-' expression
        # The expression should be a channel variable
        chan_expr = ctx.expression()
        self.visit(chan_expr)

        # Try to get channel name and look up element type
        if isinstance(chan_expr, ZincParser.PrimaryExprContext):
            primary = chan_expr.primaryExpression()
            if primary and primary.IDENTIFIER():
                channel_name = primary.IDENTIFIER().getText()
                if channel_name in self._channel_infos:
                    elem_type = self._channel_infos[channel_name].element_type
                    self.symbols.define_temp(
                        resolved_type=elem_type,
                        interval=ctx.getSourceInterval(),
                    )
                    return elem_type

        self.symbols.define_temp(
            resolved_type=BaseType.UNKNOWN,
            interval=ctx.getSourceInterval(),
        )
        return BaseType.UNKNOWN
