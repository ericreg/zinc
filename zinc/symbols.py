"""Symbol Table for the Zinc compiler."""

from dataclasses import dataclass
from enum import Enum, auto

from antlr4 import ParserRuleContext

from zinc.ast.types import BaseType, TypeInfo, parse_literal, is_mutating_method, type_to_rust, ChannelTypeInfo
from zinc.parser.zincVisitor import zincVisitor
from zinc.parser.zincParser import zincParser as ZincParser
from zinc.atlas import Atlas, FunctionInstance, ConstInstance, StructFieldInfo, StructMethodInfo


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
    element_type: BaseType | None = None  # For arrays: type of elements


class SymbolTable:
    """Scoped symbol table with lookup by id or source interval."""

    def __init__(self):
        self._symbols: list[Symbol] = []
        self._by_interval: dict[str, Symbol] = {}  # "scope:(start, stop)" -> Symbol
        self._scope_stack: list[dict[str, Symbol]] = [{}]  # Stack of id -> Symbol
        self._temp_counter: int = 0
        self._scope_path: list[str] = []  # e.g., ["main", "if_0"]
        self._function_scope: str = ""  # Top-level function scope for interval keys

    @property
    def current_scope(self) -> str:
        """Return current scope path like 'main.if_0'."""
        return ".".join(self._scope_path) if self._scope_path else "global"

    def _interval_key(self, interval: tuple[int, int]) -> str:
        """Create a scoped key for interval lookup.

        Includes function scope to distinguish same source intervals
        in different specializations of the same generic function.
        """
        return f"{self._function_scope}:({interval[0]}, {interval[1]})"

    def enter_scope(self, name: str) -> None:
        """Enter a new scope (function, if block, for loop, etc.)."""
        self._scope_path.append(name)
        self._scope_stack.append({})
        # Track function-level scope for interval keys
        if len(self._scope_path) == 1:
            self._function_scope = name

    def exit_scope(self) -> None:
        """Exit current scope."""
        self._scope_path.pop()
        self._scope_stack.pop()
        # Clear function scope when exiting function level
        if len(self._scope_path) == 0:
            self._function_scope = ""

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
        self._by_interval[self._interval_key(interval)] = symbol
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
        self._by_interval[self._interval_key(interval)] = symbol
        return symbol

    def lookup_by_id(self, id: str) -> Symbol | None:
        """Look up symbol by name in current and enclosing scopes."""
        for scope in reversed(self._scope_stack):
            if id in scope:
                return scope[id]
        return None

    def lookup_by_interval(
        self, interval: tuple[int, int], function_scope: str | None = None
    ) -> Symbol | None:
        """Look up symbol by source interval.

        Args:
            interval: The (start, stop) source interval
            function_scope: Optional function scope name (e.g., "add_i64_f64").
                           If provided, looks up in that function's context.
                           If None, uses the current function scope.
        """
        scope = function_scope if function_scope is not None else self._function_scope
        key = f"{scope}:({interval[0]}, {interval[1]})"
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

        # Analyze structs before processing functions
        for struct in self.atlas.structs.values():
            self._analyze_struct(struct)

        # Two-phase processing to handle function return types correctly:
        # Phase 1: Discover all specializations (process callers first to find call sites)
        # Phase 2: Resolve all functions in proper order (callees first for return types)

        processed: set[str] = set()

        # Phase 1: Discovery - process in caller-first order to discover specializations
        while True:
            new_work = False
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

        # Phase 2: Re-resolve in callees-first order to get correct return types
        # for function call expressions
        order = self.atlas.topological_order()  # callees first
        for mangled_name in order:
            func = self.atlas.functions[mangled_name]
            self._resolve_function(func)

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

    def _analyze_struct(self, struct) -> None:
        """Analyze a struct declaration and populate fields/methods."""
        ctx = struct.ctx

        # Parse fields
        struct.fields = self._parse_struct_fields(ctx)

        # Build field type map for parameter inference
        field_types: dict[str, str] = {}
        for f in struct.fields:
            field_types[f.name] = f.rust_type()

        # Analyze methods
        struct.methods = []
        if ctx.structBody():
            for member in ctx.structBody().structMember():
                if member.functionDeclaration():
                    method = self._analyze_struct_method(
                        member.functionDeclaration(), field_types, struct.name
                    )
                    struct.methods.append(method)

    def _parse_struct_fields(self, ctx) -> list[StructFieldInfo]:
        """Parse struct field declarations from parse tree."""
        fields = []
        if not ctx.structBody():
            return fields

        for member in ctx.structBody().structMember():
            if not member.structField():
                continue

            field_ctx = member.structField()

            # Check for const modifier - it's the first child if present
            is_const = False
            first_child = field_ctx.getChild(0)
            if first_child and first_child.getText() == "const":
                is_const = True

            name = field_ctx.IDENTIFIER().getText()
            type_ann = None
            default_val = None
            resolved_type = BaseType.UNKNOWN

            # Field can have type annotation OR default value expression
            if field_ctx.type_():
                type_ann = field_ctx.type_().getText()
                # Map to BaseType
                type_map = {
                    "i32": BaseType.INTEGER,
                    "i64": BaseType.INTEGER,
                    "f32": BaseType.FLOAT,
                    "f64": BaseType.FLOAT,
                    "string": BaseType.STRING,
                    "bool": BaseType.BOOLEAN,
                }
                resolved_type = type_map.get(type_ann.lower(), BaseType.UNKNOWN)
            elif field_ctx.expression():
                default_val = field_ctx.expression().getText()
                # Try to infer type from literal
                try:
                    resolved_type = parse_literal(default_val)
                except ValueError:
                    resolved_type = BaseType.UNKNOWN

            fields.append(
                StructFieldInfo(
                    name=name,
                    type_annotation=type_ann,
                    default_value=default_val,
                    is_private=name.startswith("_"),
                    is_const=is_const,
                    resolved_type=resolved_type,
                )
            )

        return fields

    def _analyze_struct_method(
        self, ctx: ZincParser.FunctionDeclarationContext, field_types: dict[str, str], struct_name: str
    ) -> StructMethodInfo:
        """Analyze a struct method for static/instance and self mutability."""
        name = ctx.IDENTIFIER().getText()

        # Parse parameters
        parameters: list[tuple[str, str | None, str | None]] = []
        if ctx.parameterList():
            for param_ctx in ctx.parameterList().parameter():
                param_name = param_ctx.IDENTIFIER().getText()
                param_type = param_ctx.type_().getText() if param_ctx.type_() else None
                parameters.append((param_name, param_type, None))

        # Track self usage in method body
        self_reads, self_writes = self._track_self_usage(ctx.block())

        # Determine static vs instance
        is_static = not (self_reads or self_writes)
        if is_static:
            self_mutability = None
        elif self_writes:
            self_mutability = "&mut self"
        else:
            self_mutability = "&self"

        # Infer parameter types from usage
        resolved_params = self._infer_method_params(ctx.block(), parameters, field_types)

        # Infer return type
        return_type = self._infer_return_type(ctx.block(), struct_name, field_types)

        return StructMethodInfo(
            name=name,
            parameters=resolved_params,
            is_static=is_static,
            self_mutability=self_mutability,
            return_type=return_type,
            body_ctx=ctx.block(),
        )

    def _track_self_usage(self, block_ctx) -> tuple[bool, bool]:
        """Walk a block and track self reads and writes. Returns (reads, writes)."""
        reads = False
        writes = False

        def walk(node):
            nonlocal reads, writes
            if node is None:
                return

            # Check for self.field = ... (write) - must check before read
            if isinstance(node, ZincParser.VariableAssignmentContext):
                target = node.assignmentTarget()
                # Check if target is a member access on self
                if target.memberAccess():
                    member = target.memberAccess()
                    target_expr = member.expression()
                    # Check if expression is 'self'
                    if isinstance(target_expr, ZincParser.PrimaryExprContext):
                        primary = target_expr.primaryExpression()
                        if primary and primary.getText() == "self":
                            writes = True

            # Check for self.field access (read) via member access expression
            if isinstance(node, ZincParser.MemberAccessExprContext):
                target_expr = node.expression()
                if isinstance(target_expr, ZincParser.PrimaryExprContext):
                    primary = target_expr.primaryExpression()
                    if primary and primary.getText() == "self":
                        reads = True

            # Check for self in string interpolations
            if isinstance(node, ZincParser.LiteralContext):
                if node.STRING():
                    text = node.STRING().getText()
                    if "{self." in text:
                        reads = True

            # Recurse into children
            if hasattr(node, "getChildCount"):
                for i in range(node.getChildCount()):
                    child = node.getChild(i)
                    if isinstance(child, ParserRuleContext):
                        walk(child)

        walk(block_ctx)
        return reads, writes

    def _infer_method_params(
        self, block_ctx, params: list[tuple[str, str | None, str | None]], field_types: dict[str, str]
    ) -> list[tuple[str, str | None, str | None]]:
        """Infer parameter types from method body usage."""
        param_names = {p[0] for p in params}
        inferred: dict[str, str] = {}

        def get_self_field_type(expr_ctx) -> str | None:
            """If expression is self.field, return its type."""
            if isinstance(expr_ctx, ZincParser.MemberAccessExprContext):
                target = expr_ctx.expression()
                if isinstance(target, ZincParser.PrimaryExprContext):
                    primary = target.primaryExpression()
                    if primary and primary.getText() == "self":
                        field_name = expr_ctx.IDENTIFIER().getText()
                        return field_types.get(field_name)
            return None

        def find_params_in_expr(expr_ctx) -> list[str]:
            """Find all parameter names used in an expression."""
            found = []
            def search(node):
                if node is None:
                    return
                if isinstance(node, ZincParser.PrimaryExprContext):
                    primary = node.primaryExpression()
                    if primary and primary.IDENTIFIER():
                        name = primary.IDENTIFIER().getText()
                        if name in param_names:
                            found.append(name)
                if hasattr(node, "getChildCount"):
                    for i in range(node.getChildCount()):
                        child = node.getChild(i)
                        if isinstance(child, ParserRuleContext):
                            search(child)
            search(expr_ctx)
            return found

        def walk(node):
            if node is None:
                return

            # Check for return statements with struct instantiation
            if isinstance(node, ZincParser.ReturnStatementContext):
                if node.expression():
                    expr = node.expression()
                    # Check if returning struct instantiation
                    if isinstance(expr, ZincParser.PrimaryExprContext):
                        primary = expr.primaryExpression()
                        if primary and primary.structInstantiation():
                            inst = primary.structInstantiation()
                            for field_init in inst.fieldInit():
                                field_name = field_init.IDENTIFIER().getText()
                                field_value = field_init.expression().getText()
                                # If field value is a parameter name
                                if field_value in param_names and field_name in field_types:
                                    inferred[field_value] = field_types[field_name]

            # Check for self.field = expr assignments
            if isinstance(node, ZincParser.VariableAssignmentContext):
                target = node.assignmentTarget()
                if target.memberAccess():
                    member = target.memberAccess()
                    target_expr = member.expression()
                    if isinstance(target_expr, ZincParser.PrimaryExprContext):
                        primary = target_expr.primaryExpression()
                        if primary and primary.getText() == "self":
                            field_name = member.IDENTIFIER().getText()
                            field_type = field_types.get(field_name)
                            if field_type:
                                # Find params used in the RHS expression
                                rhs_expr = node.expression()
                                params_in_rhs = find_params_in_expr(rhs_expr)
                                for param_name in params_in_rhs:
                                    if param_name not in inferred:
                                        inferred[param_name] = field_type

            # Check for binary expressions mixing self.field and params
            if isinstance(node, (ZincParser.AdditiveExprContext, ZincParser.MultiplicativeExprContext)):
                left = node.expression(0)
                right = node.expression(1)
                left_type = get_self_field_type(left)
                right_type = get_self_field_type(right)
                # If one side is a self.field, infer type for params on the other side
                if left_type:
                    params_in_right = find_params_in_expr(right)
                    for param_name in params_in_right:
                        if param_name not in inferred:
                            inferred[param_name] = left_type
                if right_type:
                    params_in_left = find_params_in_expr(left)
                    for param_name in params_in_left:
                        if param_name not in inferred:
                            inferred[param_name] = right_type

            # Recurse
            if hasattr(node, "getChildCount"):
                for i in range(node.getChildCount()):
                    child = node.getChild(i)
                    if isinstance(child, ParserRuleContext):
                        walk(child)

        walk(block_ctx)

        # Build result with inferred types
        result = []
        for name, type_ann, _ in params:
            resolved = inferred.get(name)
            result.append((name, type_ann, resolved))
        return result

    def _infer_return_type(self, block_ctx, struct_name: str, field_types: dict[str, str]) -> str | None:
        """Infer return type from return statements."""

        def get_expr_type(expr_ctx) -> str | None:
            """Get type of an expression if we can infer it."""
            if expr_ctx is None:
                return None

            # Struct instantiation
            if isinstance(expr_ctx, ZincParser.PrimaryExprContext):
                primary = expr_ctx.primaryExpression()
                if primary and primary.structInstantiation():
                    inst_name = primary.structInstantiation().IDENTIFIER().getText()
                    if inst_name == struct_name:
                        return "Self"
                    return inst_name
                if primary and primary.literal():
                    try:
                        literal_type = parse_literal(primary.literal().getText())
                        return type_to_rust(literal_type)
                    except ValueError:
                        pass

            # self.field access
            if isinstance(expr_ctx, ZincParser.MemberAccessExprContext):
                target_expr = expr_ctx.expression()
                if isinstance(target_expr, ZincParser.PrimaryExprContext):
                    primary = target_expr.primaryExpression()
                    if primary and primary.getText() == "self":
                        field_name = expr_ctx.IDENTIFIER().getText()
                        return field_types.get(field_name)

            # Binary expressions - infer from operands
            if isinstance(expr_ctx, (ZincParser.AdditiveExprContext, ZincParser.MultiplicativeExprContext)):
                left_type = get_expr_type(expr_ctx.expression(0))
                right_type = get_expr_type(expr_ctx.expression(1))
                # Return the first non-None type (both should be same for valid ops)
                return left_type or right_type

            # Parenthesized expression
            if isinstance(expr_ctx, ZincParser.ParenExprContext):
                return get_expr_type(expr_ctx.expression())

            return None

        def find_return_type(node) -> str | None:
            if node is None:
                return None

            if isinstance(node, ZincParser.ReturnStatementContext):
                if not node.expression():
                    return None
                return get_expr_type(node.expression())

            # Recurse
            if hasattr(node, "getChildCount"):
                for i in range(node.getChildCount()):
                    child = node.getChild(i)
                    if isinstance(child, ParserRuleContext):
                        result = find_return_type(child)
                        if result:
                            return result
            return None

        return find_return_type(block_ctx)

    def _is_empty_array_literal(self, expr_ctx) -> bool:
        """Check if an expression is an empty array literal []."""
        if isinstance(expr_ctx, ZincParser.PrimaryExprContext):
            primary = expr_ctx.primaryExpression()
            if primary and primary.arrayLiteral():
                arr_lit = primary.arrayLiteral()
                # Empty if no expressions inside
                return len(arr_lit.expression()) == 0
        return False

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

                        # For push on arrays, track element type
                        if (
                            method_name == "push"
                            and var_symbol.resolved_type == BaseType.ARRAY
                            and arg_types
                        ):
                            if var_symbol.element_type is None:
                                var_symbol.element_type = arg_types[0]

        # Create specialization for user-defined functions
        if isinstance(callee_ctx, ZincParser.PrimaryExprContext):
            primary = callee_ctx.primaryExpression()
            if primary and primary.IDENTIFIER():
                func_name = primary.IDENTIFIER().getText()
                if func_name not in ("print", "chan"):
                    # Look up function definition
                    func_def = self.atlas.function_defs.get(func_name)
                    # Only create specialization if all arg types are known
                    if func_def and arg_types and BaseType.UNKNOWN not in arg_types:
                        # Create specialization in Atlas (pass caller for call graph)
                        mangled = self.atlas.add_specialization(
                            func_name, arg_types, func_def, self._current_function
                        )
                        # Store mapping from call site to mangled name
                        self.specialization_map[ctx.getSourceInterval()] = mangled

                        # If this specialization has already been processed, use its return type
                        func_instance = self.atlas.functions.get(mangled)
                        if func_instance and func_instance.return_type != BaseType.VOID:
                            self.symbols.define_temp(
                                resolved_type=func_instance.return_type,
                                interval=ctx.getSourceInterval(),
                            )
                            return func_instance.return_type

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
                            # Only create new ChannelTypeInfo if it doesn't exist or has UNKNOWN type
                            # This preserves type info learned from previous passes
                            existing_chan = self._channel_infos.get(var_name)
                            if existing_chan is None or existing_chan.element_type == BaseType.UNKNOWN:
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
            elif (
                expr_type == BaseType.ARRAY
                and existing.element_type is not None
                and self._is_empty_array_literal(ctx.expression())
            ):
                # Reassigning empty array to existing array that has element type
                # This is likely shadowing with a different element type
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
