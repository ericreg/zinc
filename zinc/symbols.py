"""Symbol Table for the Zinc compiler."""

from dataclasses import dataclass, replace
from enum import Enum, auto

from antlr4 import ParserRuleContext

from zinc.ast.types import (
    BaseType,
    TypeInfo,
    parse_literal,
    is_mutating_method,
    type_to_rust,
    promote_numeric,
    ChannelTypeInfo,
    ArrayTypeInfo,
    DictTypeInfo,
    SetTypeInfo,
    TupleTypeInfo,
)
from zinc.exceptions import ZincTypeError
from zinc.parser.zincVisitor import zincVisitor
from zinc.parser.zincParser import zincParser as ZincParser
from zinc.atlas import Atlas, FunctionInstance, ConstInstance, StructFieldInfo, StructInstance, StructMethodInfo
from zinc.modules import extract_identifier_path, struct_composition_from_ctx, struct_path_from_ctx


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
    dict_info: DictTypeInfo | None = None
    set_info: SetTypeInfo | None = None
    tuple_info: TupleTypeInfo | None = None


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
        self.module_graph = atlas.module_graph
        self.symbols = SymbolTable()
        self._block_counters: dict[str, int] = {}  # For unique block names
        self._current_function: str | None = None
        self._current_module: str | None = None
        self._current_return_type: BaseType = BaseType.VOID  # Track return type during resolution
        self._current_return_dict_info: DictTypeInfo | None = None
        self._current_return_set_info: SetTypeInfo | None = None
        self._current_return_tuple_info: TupleTypeInfo | None = None
        # Maps (caller_function, call_site_interval) -> mangled name for CodeGen to use
        # Scoped by caller function to handle different specializations of the same generic
        self.specialization_map: dict[tuple[str | None, tuple[int, int]], str] = {}
        # Track channel variables and their type info (var_name -> ChannelTypeInfo)
        self._channel_infos: dict[str, ChannelTypeInfo] = {}
        # Track all caller channel infos for function parameters (param_name -> list of ChannelTypeInfos)
        self._channel_param_all_infos: dict[str, list[ChannelTypeInfo]] = {}
        self._iterating_dict_stack: list[set[str]] = []
        self._struct_analysis_cache: dict[str, StructInstance] = {}
        self._struct_analysis_stack: list[str] = []

    def _resolve_const_symbol(self, path: list[str]) -> ConstInstance | None:
        """Resolve a const path in the current module."""
        if self._current_module is None:
            return None
        symbol = self.module_graph.resolve_const_path(self._current_module, path)
        if symbol is None:
            return None
        return self.atlas.consts.get(symbol.qualified_name) or ConstInstance(
            name=symbol.name,
            qualified_name=symbol.qualified_name,
            module_id=symbol.module_id,
            ctx=symbol.ctx,
        )

    def _resolve_function_symbol(self, path: list[str]):
        """Resolve a function path in the current module."""
        if self._current_module is None:
            return None
        return self.module_graph.resolve_function_path(self._current_module, path)

    def _resolve_struct_symbol(self, path: list[str]):
        """Resolve a struct path in the current module."""
        if self._current_module is None:
            return None
        return self.module_graph.resolve_struct_path(self._current_module, path)

    def _method_return_base_type(self, return_type: str | None) -> BaseType:
        """Map an analyzed method return type string to a base type."""
        if return_type is None:
            return BaseType.VOID
        mapping = {
            "i8": BaseType.INTEGER,
            "i16": BaseType.INTEGER,
            "i32": BaseType.INTEGER,
            "i64": BaseType.INTEGER,
            "i128": BaseType.INTEGER,
            "u8": BaseType.INTEGER,
            "u16": BaseType.INTEGER,
            "u32": BaseType.INTEGER,
            "u64": BaseType.INTEGER,
            "u128": BaseType.INTEGER,
            "f8": BaseType.FLOAT,
            "f16": BaseType.FLOAT,
            "f32": BaseType.FLOAT,
            "f64": BaseType.FLOAT,
            "f128": BaseType.FLOAT,
            "String": BaseType.STRING,
            "string": BaseType.STRING,
            "bool": BaseType.BOOLEAN,
            "Self": BaseType.STRUCT,
        }
        return mapping.get(return_type, BaseType.UNKNOWN)

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
        for name, base_type in (
            ("dict", BaseType.DICT),
            ("sort_dict", BaseType.DICT),
            ("set", BaseType.SET),
            ("sort_set", BaseType.SET),
        ):
            self.symbols.define(
                id=name,
                kind=SymbolKind.BUILTIN,
                resolved_type=base_type,
                interval=(-1, -1),
            )

    def _analyze_struct(self, struct) -> None:
        """Analyze a struct declaration and populate fields/methods."""
        analyzed = self._analyze_struct_by_qualified_name(struct.qualified_name)
        struct.fields = [self._copy_struct_field(field) for field in analyzed.fields]
        struct.methods = [self._copy_struct_method(method) for method in analyzed.methods]
        struct.composition_mode = analyzed.composition_mode
        struct.composition_sources = analyzed.composition_sources

    def _analyze_struct_by_qualified_name(self, qualified_name: str) -> StructInstance:
        """Analyze a struct definition, including flattening any composition."""
        cached = self._struct_analysis_cache.get(qualified_name)
        if cached is not None:
            return cached

        if qualified_name in self._struct_analysis_stack:
            cycle = " -> ".join([*self._struct_analysis_stack, qualified_name])
            raise ZincTypeError(f"cyclic struct composition is not supported: {cycle}")

        symbol = self.module_graph.get_symbol(qualified_name)
        ctx: ZincParser.StructDeclarationContext = symbol.ctx  # type: ignore[assignment]
        struct = StructInstance(
            name=symbol.name,
            qualified_name=symbol.qualified_name,
            module_id=symbol.module_id,
            ctx=symbol.ctx,
        )

        self._struct_analysis_stack.append(qualified_name)
        try:
            composition = struct_composition_from_ctx(ctx)
            fields: list[StructFieldInfo] = []
            field_indexes: dict[str, int] = {}
            methods: list[StructMethodInfo] = []
            method_indexes: dict[str, int] = {}

            if composition is not None:
                struct.composition_mode = composition.mode
                source_names: list[str] = []
                allow_override = composition.mode == "merge"

                for source_path in composition.source_paths:
                    source_display = ".".join(source_path)
                    source_symbol = self.module_graph.resolve_struct_path(
                        symbol.module_id, list(source_path)
                    )
                    if source_symbol is None:
                        raise ZincTypeError(
                            f"unknown struct composition source '{source_display}' in '{symbol.name}'"
                        )
                    if source_symbol.qualified_name == qualified_name:
                        raise ZincTypeError(f"struct '{symbol.name}' cannot compose itself")
                    source_names.append(source_symbol.qualified_name)
                    source_struct = self._analyze_struct_by_qualified_name(
                        source_symbol.qualified_name
                    )
                    self._merge_struct_fields(
                        owner_name=symbol.name,
                        mode=composition.mode,
                        fields=fields,
                        field_indexes=field_indexes,
                        incoming=source_struct.fields,
                        allow_override=allow_override,
                    )
                    self._merge_struct_methods(
                        owner_name=symbol.name,
                        mode=composition.mode,
                        methods=methods,
                        method_indexes=method_indexes,
                        incoming=source_struct.methods,
                        allow_override=allow_override,
                    )

                struct.composition_sources = tuple(source_names)

            local_fields = self._parse_struct_fields(ctx, qualified_name)
            self._merge_struct_fields(
                owner_name=symbol.name,
                mode=struct.composition_mode,
                fields=fields,
                field_indexes=field_indexes,
                incoming=local_fields,
                allow_override=struct.composition_mode == "merge",
            )

            field_types = {field.name: field.rust_type() for field in fields}

            local_methods: list[StructMethodInfo] = []
            if ctx.structBody():
                for member in ctx.structBody().structMember():
                    if member.functionDeclaration():
                        local_methods.append(
                            self._analyze_struct_method(
                                member.functionDeclaration(),
                                field_types,
                                source_module_id=symbol.module_id,
                                constructor_owner_qualified_name=qualified_name,
                            )
                        )

            self._merge_struct_methods(
                owner_name=symbol.name,
                mode=struct.composition_mode,
                methods=methods,
                method_indexes=method_indexes,
                incoming=local_methods,
                allow_override=struct.composition_mode == "merge",
            )

            if struct.composition_mode is not None:
                self._validate_composed_struct_methods(symbol.name, fields, methods)

            struct.fields = fields
            struct.methods = methods
            self._struct_analysis_cache[qualified_name] = struct
            return struct
        finally:
            self._struct_analysis_stack.pop()

    def _copy_struct_field(self, field: StructFieldInfo) -> StructFieldInfo:
        """Clone field metadata when flattening composition."""
        return replace(field)

    def _copy_struct_method(self, method: StructMethodInfo) -> StructMethodInfo:
        """Clone method metadata when flattening composition."""
        return replace(
            method,
            parameters=[(name, type_ann, resolved) for name, type_ann, resolved in method.parameters],
        )

    def _merge_struct_fields(
        self,
        owner_name: str,
        mode: str | None,
        fields: list[StructFieldInfo],
        field_indexes: dict[str, int],
        incoming: list[StructFieldInfo],
        allow_override: bool,
    ) -> None:
        """Merge fields into a flattened struct, optionally allowing overrides."""
        for field in incoming:
            copied = self._copy_struct_field(field)
            existing_index = field_indexes.get(copied.name)
            if existing_index is None:
                field_indexes[copied.name] = len(fields)
                fields.append(copied)
                continue
            if not allow_override:
                previous = fields[existing_index]
                raise ZincTypeError(
                    f"orthogonal composition for '{owner_name}' has duplicate field "
                    f"'{copied.name}' from '{self._member_source_name(previous.source_struct_qualified_name)}' "
                    f"and '{self._member_source_name(copied.source_struct_qualified_name)}'"
                )
            fields[existing_index] = copied

    def _merge_struct_methods(
        self,
        owner_name: str,
        mode: str | None,
        methods: list[StructMethodInfo],
        method_indexes: dict[str, int],
        incoming: list[StructMethodInfo],
        allow_override: bool,
    ) -> None:
        """Merge methods into a flattened struct, optionally allowing overrides."""
        for method in incoming:
            copied = self._copy_struct_method(method)
            existing_index = method_indexes.get(copied.name)
            if existing_index is None:
                method_indexes[copied.name] = len(methods)
                methods.append(copied)
                continue
            if not allow_override:
                previous = methods[existing_index]
                raise ZincTypeError(
                    f"orthogonal composition for '{owner_name}' has duplicate method "
                    f"'{copied.name}' from '{self._member_source_name(previous.source_struct_qualified_name)}' "
                    f"and '{self._member_source_name(copied.source_struct_qualified_name)}'"
                )
            methods[existing_index] = copied

    def _member_source_name(self, qualified_name: str | None) -> str:
        """Render a human-readable source-struct name for diagnostics."""
        if qualified_name is None:
            return "local"
        return self.module_graph.get_symbol(qualified_name).name

    def _parse_struct_fields(self, ctx, source_struct_qualified_name: str) -> list[StructFieldInfo]:
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
                    "i8": BaseType.INTEGER,
                    "i16": BaseType.INTEGER,
                    "i32": BaseType.INTEGER,
                    "i64": BaseType.INTEGER,
                    "i128": BaseType.INTEGER,
                    "u8": BaseType.INTEGER,
                    "u16": BaseType.INTEGER,
                    "u32": BaseType.INTEGER,
                    "u64": BaseType.INTEGER,
                    "u128": BaseType.INTEGER,
                    "f8": BaseType.FLOAT,
                    "f16": BaseType.FLOAT,
                    "f32": BaseType.FLOAT,
                    "f64": BaseType.FLOAT,
                    "f128": BaseType.FLOAT,
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
                    source_struct_qualified_name=source_struct_qualified_name,
                )
            )

        return fields

    def _analyze_struct_method(
        self,
        ctx: ZincParser.FunctionDeclarationContext,
        field_types: dict[str, str],
        source_module_id: str,
        constructor_owner_qualified_name: str,
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
        return_type = self._infer_return_type(
            ctx.block(),
            field_types,
            source_module_id,
            constructor_owner_qualified_name,
        )

        return StructMethodInfo(
            name=name,
            parameters=resolved_params,
            is_static=is_static,
            self_mutability=self_mutability,
            return_type=return_type,
            body_ctx=ctx.block(),
            source_struct_qualified_name=constructor_owner_qualified_name,
            source_module_id=source_module_id,
            constructor_owner_qualified_name=constructor_owner_qualified_name,
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

    def _infer_return_type(
        self,
        block_ctx,
        field_types: dict[str, str],
        source_module_id: str,
        constructor_owner_qualified_name: str,
    ) -> str | None:
        """Infer return type from return statements."""

        def get_expr_type(expr_ctx) -> str | None:
            """Get type of an expression if we can infer it."""
            if expr_ctx is None:
                return None

            # Struct instantiation
            if isinstance(expr_ctx, ZincParser.PrimaryExprContext):
                primary = expr_ctx.primaryExpression()
                if primary and primary.structInstantiation():
                    inst = primary.structInstantiation()
                    struct_symbol = self.module_graph.resolve_struct_path(
                        source_module_id, struct_path_from_ctx(inst)
                    )
                    if (
                        struct_symbol is not None
                        and struct_symbol.qualified_name == constructor_owner_qualified_name
                    ):
                        return "Self"
                    return inst.qualifiedName().getText()
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

    def _validate_composed_struct_methods(
        self,
        struct_name: str,
        fields: list[StructFieldInfo],
        methods: list[StructMethodInfo],
    ) -> None:
        """Validate copied methods against the final flattened field set."""
        field_types = {
            field.name: self._type_name_to_base(field.type_annotation or field.rust_type())
            for field in fields
        }
        method_types = {method.name: self._method_return_base_type(method.return_type) for method in methods}

        for method in methods:
            param_types = {
                name: self._type_name_to_base(resolved or type_ann)
                for name, type_ann, resolved in method.parameters
            }
            self._validate_composed_method_node(
                node=method.body_ctx,
                struct_name=struct_name,
                method_name=method.name,
                field_types=field_types,
                method_types=method_types,
                param_types=param_types,
            )

    def _validate_composed_method_node(
        self,
        node,
        struct_name: str,
        method_name: str,
        field_types: dict[str, BaseType],
        method_types: dict[str, BaseType],
        param_types: dict[str, BaseType],
    ) -> None:
        """Walk a composed method body and reject obviously invalid self usage."""
        if node is None:
            return

        if isinstance(node, ZincParser.VariableAssignmentContext):
            target = node.assignmentTarget()
            if target.memberAccess():
                member = target.memberAccess()
                target_expr = member.expression()
                if isinstance(target_expr, ZincParser.PrimaryExprContext):
                    primary = target_expr.primaryExpression()
                    if primary and primary.getText() == "self":
                        field_name = member.IDENTIFIER().getText()
                        expected = field_types.get(field_name)
                        if expected is None:
                            raise ZincTypeError(
                                f"composed method '{struct_name}.{method_name}' references missing field '{field_name}'"
                            )
                        actual = self._composed_expr_type(
                            node.expression(),
                            struct_name,
                            method_name,
                            field_types,
                            method_types,
                            param_types,
                        )
                        if not self._assignment_types_compatible(expected, actual):
                            raise ZincTypeError(
                                f"composed method '{struct_name}.{method_name}' assigns incompatible value to field '{field_name}'"
                            )

        if isinstance(node, ZincParser.FunctionCallExprContext):
            callee_ctx = node.expression()
            if isinstance(callee_ctx, ZincParser.MemberAccessExprContext):
                receiver = callee_ctx.expression()
                if isinstance(receiver, ZincParser.PrimaryExprContext):
                    primary = receiver.primaryExpression()
                    if primary and primary.getText() == "self":
                        callee_name = callee_ctx.IDENTIFIER().getText()
                        if callee_name not in method_types:
                            raise ZincTypeError(
                                f"composed method '{struct_name}.{method_name}' calls missing method '{callee_name}'"
                            )

        if isinstance(node, ZincParser.MemberAccessExprContext):
            target_expr = node.expression()
            if isinstance(target_expr, ZincParser.PrimaryExprContext):
                primary = target_expr.primaryExpression()
                if primary and primary.getText() == "self":
                    field_name = node.IDENTIFIER().getText()
                    if field_name not in field_types and field_name not in method_types:
                        raise ZincTypeError(
                            f"composed method '{struct_name}.{method_name}' references missing member '{field_name}'"
                        )

        if hasattr(node, "getChildCount"):
            for i in range(node.getChildCount()):
                child = node.getChild(i)
                if isinstance(child, ParserRuleContext):
                    self._validate_composed_method_node(
                        child,
                        struct_name,
                        method_name,
                        field_types,
                        method_types,
                        param_types,
                    )

    def _composed_expr_type(
        self,
        expr_ctx,
        struct_name: str,
        method_name: str,
        field_types: dict[str, BaseType],
        method_types: dict[str, BaseType],
        param_types: dict[str, BaseType],
    ) -> BaseType:
        """Infer a lightweight type for composed-method validation."""
        if expr_ctx is None:
            return BaseType.UNKNOWN

        if isinstance(expr_ctx, ZincParser.PrimaryExprContext):
            primary = expr_ctx.primaryExpression()
            if primary is None:
                return BaseType.UNKNOWN
            if primary.literal():
                return parse_literal(primary.literal().getText())
            if primary.IDENTIFIER():
                return param_types.get(primary.IDENTIFIER().getText(), BaseType.UNKNOWN)
            if primary.structInstantiation():
                return BaseType.STRUCT
            if primary.getText() == "self":
                return BaseType.STRUCT
            return BaseType.UNKNOWN

        if isinstance(expr_ctx, ZincParser.MemberAccessExprContext):
            receiver = expr_ctx.expression()
            if isinstance(receiver, ZincParser.PrimaryExprContext):
                primary = receiver.primaryExpression()
                if primary and primary.getText() == "self":
                    member_name = expr_ctx.IDENTIFIER().getText()
                    if member_name in field_types:
                        return field_types[member_name]
                    if member_name in method_types:
                        return method_types[member_name]
                    raise ZincTypeError(
                        f"composed method '{struct_name}.{method_name}' references missing member '{member_name}'"
                    )
            return BaseType.UNKNOWN

        if isinstance(expr_ctx, ZincParser.ParenExprContext):
            return self._composed_expr_type(
                expr_ctx.expression(),
                struct_name,
                method_name,
                field_types,
                method_types,
                param_types,
            )

        if isinstance(expr_ctx, ZincParser.UnaryExprContext):
            operand = self._composed_expr_type(
                expr_ctx.expression(),
                struct_name,
                method_name,
                field_types,
                method_types,
                param_types,
            )
            return BaseType.BOOLEAN if expr_ctx.getChild(0).getText() in {"!", "not"} else operand

        if isinstance(expr_ctx, (ZincParser.AdditiveExprContext, ZincParser.MultiplicativeExprContext)):
            left = self._composed_expr_type(
                expr_ctx.expression(0),
                struct_name,
                method_name,
                field_types,
                method_types,
                param_types,
            )
            right = self._composed_expr_type(
                expr_ctx.expression(1),
                struct_name,
                method_name,
                field_types,
                method_types,
                param_types,
            )
            result = TypeInfo.promote(TypeInfo(left), TypeInfo(right)).base
            if result == BaseType.UNKNOWN and left != BaseType.UNKNOWN and right != BaseType.UNKNOWN:
                raise ZincTypeError(
                    f"composed method '{struct_name}.{method_name}' uses incompatible operand types"
                )
            return result

        if isinstance(expr_ctx, (ZincParser.RelationalExprContext, ZincParser.EqualityExprContext)):
            return BaseType.BOOLEAN

        if isinstance(expr_ctx, (ZincParser.LogicalAndExprContext, ZincParser.LogicalOrExprContext)):
            return BaseType.BOOLEAN

        if isinstance(expr_ctx, ZincParser.FunctionCallExprContext):
            callee_ctx = expr_ctx.expression()
            if isinstance(callee_ctx, ZincParser.MemberAccessExprContext):
                receiver = callee_ctx.expression()
                if isinstance(receiver, ZincParser.PrimaryExprContext):
                    primary = receiver.primaryExpression()
                    if primary and primary.getText() == "self":
                        callee_name = callee_ctx.IDENTIFIER().getText()
                        if callee_name not in method_types:
                            raise ZincTypeError(
                                f"composed method '{struct_name}.{method_name}' calls missing method '{callee_name}'"
                            )
                        return method_types[callee_name]
            return BaseType.UNKNOWN

        return BaseType.UNKNOWN

    def _type_name_to_base(self, type_name: str | None) -> BaseType:
        """Map a Rust-or-Zinc type spelling to a base type."""
        if type_name is None:
            return BaseType.UNKNOWN
        mapping = {
            "i8": BaseType.INTEGER,
            "i16": BaseType.INTEGER,
            "i32": BaseType.INTEGER,
            "i64": BaseType.INTEGER,
            "i128": BaseType.INTEGER,
            "u8": BaseType.INTEGER,
            "u16": BaseType.INTEGER,
            "u32": BaseType.INTEGER,
            "u64": BaseType.INTEGER,
            "u128": BaseType.INTEGER,
            "f8": BaseType.FLOAT,
            "f16": BaseType.FLOAT,
            "f32": BaseType.FLOAT,
            "f64": BaseType.FLOAT,
            "f128": BaseType.FLOAT,
            "String": BaseType.STRING,
            "string": BaseType.STRING,
            "bool": BaseType.BOOLEAN,
            "Self": BaseType.STRUCT,
        }
        return mapping.get(type_name, BaseType.UNKNOWN)

    def _assignment_types_compatible(self, expected: BaseType, actual: BaseType) -> bool:
        """Return True when an assignment is compatible under Zinc's simple rules."""
        if expected == BaseType.UNKNOWN or actual == BaseType.UNKNOWN:
            return True
        if expected == actual:
            return True
        return expected in {BaseType.INTEGER, BaseType.FLOAT} and actual in {BaseType.INTEGER, BaseType.FLOAT}

    def _is_empty_array_literal(self, expr_ctx) -> bool:
        """Check if an expression is an empty array literal []."""
        if isinstance(expr_ctx, ZincParser.PrimaryExprContext):
            primary = expr_ctx.primaryExpression()
            if primary and primary.arrayLiteral():
                arr_lit = primary.arrayLiteral()
                # Empty if no expressions inside
                return len(arr_lit.expression()) == 0
        return False

    def _copy_dict_info(self, info: DictTypeInfo | None) -> DictTypeInfo | None:
        """Copy dict metadata so symbols do not accidentally share construction state."""
        if info is None:
            return None
        return DictTypeInfo(
            key_type=info.key_type,
            value_type=info.value_type,
            kind=info.kind,
            is_mutated=info.is_mutated,
        )

    def _copy_set_info(self, info: SetTypeInfo | None) -> SetTypeInfo | None:
        """Copy set metadata so symbols do not accidentally share construction state."""
        if info is None:
            return None
        return SetTypeInfo(
            element_type=info.element_type,
            kind=info.kind,
            is_mutated=info.is_mutated,
        )

    def _copy_array_info(self, info: ArrayTypeInfo | None) -> ArrayTypeInfo | None:
        """Copy array metadata, including tuple element metadata."""
        if info is None:
            return None
        return ArrayTypeInfo(
            element_type=info.element_type,
            element_tuple_info=self._copy_tuple_info(info.element_tuple_info),
            is_mutated=info.is_mutated,
        )

    def _copy_tuple_info(self, info: TupleTypeInfo | None) -> TupleTypeInfo | None:
        """Copy tuple metadata recursively."""
        if info is None:
            return None
        return TupleTypeInfo(
            element_types=list(info.element_types),
            element_tuple_infos={
                i: copied
                for i, nested in info.element_tuple_infos.items()
                if (copied := self._copy_tuple_info(nested)) is not None
            },
        )

    def _is_channel_constructor_call(self, expr_ctx) -> bool:
        """Return True when an expression is a direct chan(...) call."""
        return self._function_call_name(expr_ctx) == "chan"

    def _channel_info_for_name(self, channel_name: str) -> ChannelTypeInfo:
        """Return mutable channel metadata for a resolved channel symbol."""
        symbol = self.symbols.lookup_by_id(channel_name)
        if symbol is None or symbol.resolved_type != BaseType.CHANNEL:
            raise ZincTypeError(f"'{channel_name}' is not a channel")
        info = self._channel_infos.get(channel_name)
        if info is None:
            info = ChannelTypeInfo(element_type=BaseType.UNKNOWN)
            self._channel_infos[channel_name] = info
        return info

    def _merge_channel_value_type(self, channel_name: str, value_type: BaseType) -> None:
        """Merge a sent value type into channel metadata."""
        targets = self._channel_param_all_infos.get(channel_name)
        if targets is None:
            targets = [self._channel_info_for_name(channel_name)]

        for chan_info in targets:
            if chan_info.element_type == BaseType.UNKNOWN:
                chan_info.element_type = value_type
                continue
            if value_type == BaseType.UNKNOWN or value_type == chan_info.element_type:
                continue
            merged = promote_numeric(chan_info.element_type, value_type)
            if merged == BaseType.UNKNOWN:
                raise ZincTypeError("mixed channel value types are not supported")
            chan_info.element_type = merged

    def _merge_key_type(self, current: BaseType, incoming: BaseType, label: str) -> BaseType:
        """Merge dict key or set element types, rejecting floats for Rust container keys."""
        if incoming == BaseType.FLOAT:
            raise ZincTypeError(f"{label} cannot be a float in v1")
        if current == BaseType.UNKNOWN:
            return incoming
        if incoming == BaseType.UNKNOWN or incoming == current:
            return current
        raise ZincTypeError(f"mixed {label} types are not supported")

    def _merge_value_type(self, current: BaseType, incoming: BaseType, label: str) -> BaseType:
        """Merge value types with int/float promotion."""
        merged = promote_numeric(current, incoming)
        if merged == BaseType.UNKNOWN and current != BaseType.UNKNOWN and incoming != BaseType.UNKNOWN:
            raise ZincTypeError(f"mixed {label} types are not supported")
        return merged

    def _merge_dict_info(self, current: DictTypeInfo | None, incoming: DictTypeInfo | None) -> DictTypeInfo | None:
        """Merge dict metadata from multiple sources."""
        if incoming is None:
            return current
        if current is None:
            return self._copy_dict_info(incoming)
        if current.kind != incoming.kind:
            raise ZincTypeError("function return paths use different dict kinds")
        current.key_type = self._merge_key_type(current.key_type, incoming.key_type, "dict key")
        current.value_type = self._merge_value_type(current.value_type, incoming.value_type, "dict value")
        return current

    def _merge_set_info(self, current: SetTypeInfo | None, incoming: SetTypeInfo | None) -> SetTypeInfo | None:
        """Merge set metadata from multiple sources."""
        if incoming is None:
            return current
        if current is None:
            return self._copy_set_info(incoming)
        if current.kind != incoming.kind:
            raise ZincTypeError("function return paths use different set kinds")
        current.element_type = self._merge_key_type(current.element_type, incoming.element_type, "set element")
        return current

    def _merge_tuple_info(self, current: TupleTypeInfo | None, incoming: TupleTypeInfo | None) -> TupleTypeInfo | None:
        """Merge tuple metadata from multiple return paths."""
        if incoming is None:
            return current
        if current is None:
            return self._copy_tuple_info(incoming)
        if len(current.element_types) != len(incoming.element_types):
            raise ZincTypeError("tuple return paths use different arities")
        for i, incoming_type in enumerate(incoming.element_types):
            current_type = current.element_types[i]
            if current_type == BaseType.TUPLE or incoming_type == BaseType.TUPLE:
                if current_type != BaseType.TUPLE or incoming_type != BaseType.TUPLE:
                    raise ZincTypeError("tuple return paths use incompatible element types")
                current.element_tuple_infos[i] = self._merge_tuple_info(
                    current.element_tuple_infos.get(i),
                    incoming.element_tuple_infos.get(i),
                ) or TupleTypeInfo()
                continue
            merged = promote_numeric(current_type, incoming_type)
            if merged == BaseType.UNKNOWN and current_type != BaseType.UNKNOWN and incoming_type != BaseType.UNKNOWN:
                raise ZincTypeError("tuple return paths use incompatible element types")
            current.element_types[i] = merged
        return current

    def _tuple_info_from_dict_info(self, info: DictTypeInfo) -> TupleTypeInfo:
        """Build the item tuple type for dict iteration."""
        return TupleTypeInfo(element_types=[info.key_type, info.value_type])

    def _binding_tokens(self, ctx) -> list:
        """Return identifier tokens from a binding/destructuring context."""
        return list(ctx.getTokens(ZincParser.IDENTIFIER))

    def _integer_literal_value(self, ctx) -> int | None:
        """Return an integer literal value for tuple indexes, if statically known."""
        if isinstance(ctx, ZincParser.PrimaryExprContext):
            primary = ctx.primaryExpression()
            if primary and primary.literal() and primary.literal().INTEGER():
                return int(primary.literal().getText(), 0)
        return None

    def _expr_symbol(self, ctx) -> Symbol | None:
        """Look up the symbol for an expression in the current function."""
        return self.symbols.lookup_by_interval(
            ctx.getSourceInterval(), self._current_function
        )

    def _iterated_dict_name(self, expr_ctx) -> str | None:
        """Return the dict variable name if an expression iterates a dict."""
        if isinstance(expr_ctx, ZincParser.PrimaryExprContext):
            primary = expr_ctx.primaryExpression()
            if primary and primary.IDENTIFIER():
                name = primary.IDENTIFIER().getText()
                symbol = self.symbols.lookup_by_id(name)
                if symbol and symbol.resolved_type == BaseType.DICT:
                    return name

        if isinstance(expr_ctx, ZincParser.FunctionCallExprContext):
            callee = expr_ctx.expression()
            if isinstance(callee, ZincParser.MemberAccessExprContext):
                method_name = callee.IDENTIFIER().getText()
                if method_name in {"keys", "values", "items"}:
                    receiver = callee.expression()
                    if isinstance(receiver, ZincParser.PrimaryExprContext):
                        primary = receiver.primaryExpression()
                        if primary and primary.IDENTIFIER():
                            name = primary.IDENTIFIER().getText()
                            symbol = self.symbols.lookup_by_id(name)
                            if symbol and symbol.resolved_type == BaseType.DICT:
                                return name
        return None

    def _is_iterating_dict(self, name: str) -> bool:
        """Check whether a dict variable is currently being iterated."""
        return any(name in frame for frame in self._iterating_dict_stack)

    def _function_call_name(self, expr_ctx) -> str | None:
        """Return the simple callee name for calls like dict()."""
        if isinstance(expr_ctx, ZincParser.FunctionCallExprContext):
            callee = expr_ctx.expression()
            if isinstance(callee, ZincParser.PrimaryExprContext):
                primary = callee.primaryExpression()
                if primary and primary.IDENTIFIER():
                    return primary.IDENTIFIER().getText()
        return None

    def _is_empty_collection_constructor(self, expr_ctx) -> bool:
        """Check if an expression is dict/set/sort_dict/sort_set()."""
        return self._function_call_name(expr_ctx) in {"dict", "sort_dict", "set", "sort_set"}

    def _next_block_name(self, prefix: str) -> str:
        """Generate unique block name like 'if_0', 'for_1'."""
        count = self._block_counters.get(prefix, 0)
        self._block_counters[prefix] = count + 1
        return f"{prefix}_{count}"

    def _resolve_const(self, const: ConstInstance) -> None:
        """Resolve type of a global constant."""
        ctx: ZincParser.ConstDeclarationContext = const.ctx  # type: ignore[assignment]
        previous_module = self._current_module
        self._current_module = const.module_id
        try:
            expr_type = self.visit(ctx.expression())
            self.symbols.define(
                id=const.qualified_name,
                kind=SymbolKind.CONST,
                resolved_type=expr_type,
                interval=ctx.getSourceInterval(),
            )
        finally:
            self._current_module = previous_module

    def _resolve_function(self, func: FunctionInstance) -> None:
        """Resolve types within a function body for a specific specialization."""
        self._block_counters.clear()
        self._current_function = func.mangled_name
        self._current_module = func.module_id
        self._current_return_type = BaseType.VOID  # Reset for this function
        self._current_return_dict_info = None
        self._current_return_set_info = None
        self._current_return_tuple_info = None

        # Use mangled name for scope so symbols are per-specialization
        self.symbols.enter_scope(func.mangled_name)

        # Define parameters with types from func.arg_types
        ctx = func.ctx
        # Track parameter names for mutation detection
        param_names: list[str] = []
        if hasattr(ctx, "parameterList") and ctx.parameterList():
            for i, param_ctx in enumerate(ctx.parameterList().parameter()):
                param_name = param_ctx.IDENTIFIER().getText()
                param_names.append(param_name)
                # Use arg type from specialization if available
                if i < len(func.arg_types):
                    param_type = func.arg_types[i]
                else:
                    param_type = BaseType.UNKNOWN
                param_symbol = self.symbols.define(
                    id=param_name,
                    kind=SymbolKind.PARAMETER,
                    resolved_type=param_type,
                    interval=param_ctx.getSourceInterval(),
                )
                # Track channel parameters for element type inference
                # Store the list of all caller channels for this parameter
                if param_type == BaseType.CHANNEL and i in func.arg_channel_infos:
                    # Use first one as primary reference, but store all for updating
                    all_chan_infos = func.arg_channel_infos[i]
                    if all_chan_infos:
                        self._channel_infos[param_name] = all_chan_infos[0]
                        # Store full list for updating all callers when element type is inferred
                        self._channel_param_all_infos[param_name] = all_chan_infos
                # Track array parameters for element type
                if param_type == BaseType.ARRAY and i in func.arg_array_infos:
                    param_symbol.element_type = func.arg_array_infos[i].element_type
                    param_symbol.tuple_info = self._copy_tuple_info(
                        func.arg_array_infos[i].element_tuple_info
                    )
                if param_type == BaseType.DICT and i in func.arg_dict_infos:
                    param_symbol.dict_info = self._copy_dict_info(func.arg_dict_infos[i])
                if param_type == BaseType.SET and i in func.arg_set_infos:
                    param_symbol.set_info = self._copy_set_info(func.arg_set_infos[i])
                if param_type == BaseType.TUPLE and i in func.arg_tuple_infos:
                    param_symbol.tuple_info = self._copy_tuple_info(func.arg_tuple_infos[i])

        # Visit function body (skip parameter list since we handled it)
        if hasattr(ctx, "block"):
            self.visit(ctx.block())

        self._validate_resolved_collections(func.mangled_name)

        # Store the inferred return type
        func.return_type = self._current_return_type
        func.return_dict_info = self._copy_dict_info(self._current_return_dict_info)
        func.return_set_info = self._copy_set_info(self._current_return_set_info)
        func.return_tuple_info = self._copy_tuple_info(self._current_return_tuple_info)

        # Update array parameter mutation info
        for i, param_name in enumerate(param_names):
            if i in func.arg_array_infos:
                param_symbol = self.symbols.lookup_by_id(param_name)
                if param_symbol and param_symbol.is_mutated:
                    func.arg_array_infos[i].is_mutated = True
            if i in func.arg_dict_infos:
                param_symbol = self.symbols.lookup_by_id(param_name)
                if param_symbol and param_symbol.is_mutated:
                    func.arg_dict_infos[i].is_mutated = True
            if i in func.arg_set_infos:
                param_symbol = self.symbols.lookup_by_id(param_name)
                if param_symbol and param_symbol.is_mutated:
                    func.arg_set_infos[i].is_mutated = True

        self.symbols.exit_scope()
        self._current_function = None
        self._current_module = None

    def _validate_resolved_collections(self, function_scope: str) -> None:
        """Reject empty collection types that were never constrained."""
        prefix = f"{function_scope}."
        for symbol in self.symbols.all_symbols():
            if symbol.kind not in {SymbolKind.VARIABLE, SymbolKind.PARAMETER}:
                continue
            if not symbol.unique_name.startswith(prefix):
                continue
            if (
                symbol.resolved_type == BaseType.ARRAY
                and (
                    symbol.element_type is None
                    or symbol.element_type == BaseType.UNKNOWN
                )
            ):
                raise ZincTypeError(
                    f"cannot infer type for empty array '{symbol.id}'"
                )
            if symbol.dict_info and (
                symbol.dict_info.key_type == BaseType.UNKNOWN
                or symbol.dict_info.value_type == BaseType.UNKNOWN
            ):
                raise ZincTypeError(
                    f"cannot infer type for empty {symbol.dict_info.kind} '{symbol.id}'"
                )
            if symbol.set_info and symbol.set_info.element_type == BaseType.UNKNOWN:
                raise ZincTypeError(
                    f"cannot infer type for empty {symbol.set_info.kind} '{symbol.id}'"
                )

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
                temp = self.symbols.define_temp(
                    resolved_type=symbol.resolved_type,
                    interval=ctx.getSourceInterval(),
                )
                temp.element_type = symbol.element_type
                temp.dict_info = symbol.dict_info
                temp.set_info = symbol.set_info
                temp.tuple_info = symbol.tuple_info
                return symbol.resolved_type

            const_symbol = None
            if self._current_module is not None:
                resolved_const = self.module_graph.resolve_const_path(
                    self._current_module, [name]
                )
                if resolved_const:
                    const_symbol = self.symbols.lookup_by_id(resolved_const.qualified_name)
            if const_symbol:
                self.symbols.define_temp(
                    resolved_type=const_symbol.resolved_type,
                    interval=ctx.getSourceInterval(),
                )
                return const_symbol.resolved_type
            self.symbols.define_temp(
                resolved_type=BaseType.UNKNOWN,
                interval=ctx.getSourceInterval(),
            )
            return BaseType.UNKNOWN

        if ctx.arrayLiteral():
            return self.visit(ctx.arrayLiteral())

        if ctx.collectionLiteral():
            return self.visit(ctx.collectionLiteral())

        if ctx.tupleLiteral():
            return self.visit(ctx.tupleLiteral())

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
        inner_symbol = self._expr_symbol(ctx.expression())
        self.symbols.define_temp(
            resolved_type=inner_type,
            interval=ctx.getSourceInterval(),
        ).tuple_info = self._copy_tuple_info(inner_symbol.tuple_info) if inner_symbol else None
        return inner_type

    def visitTupleLiteral(self, ctx: ZincParser.TupleLiteralContext) -> BaseType:
        """Visit tuple literal and infer element types."""
        element_types: list[BaseType] = []
        element_tuple_infos: dict[int, TupleTypeInfo] = {}
        for i, expr_ctx in enumerate(ctx.expression()):
            element_type = self.visit(expr_ctx)
            element_types.append(element_type)
            if element_type == BaseType.TUPLE:
                expr_symbol = self._expr_symbol(expr_ctx)
                if expr_symbol and expr_symbol.tuple_info:
                    copied = self._copy_tuple_info(expr_symbol.tuple_info)
                    if copied:
                        element_tuple_infos[i] = copied

        symbol = self.symbols.define_temp(
            resolved_type=BaseType.TUPLE,
            interval=ctx.getSourceInterval(),
        )
        symbol.tuple_info = TupleTypeInfo(
            element_types=element_types,
            element_tuple_infos=element_tuple_infos,
        )
        return BaseType.TUPLE

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
        """Visit array literal and infer element type from first element."""
        element_type = None
        element_tuple_info = None
        for expr_ctx in ctx.expression():
            expr_type = self.visit(expr_ctx)
            if element_type is None:
                element_type = expr_type
                if expr_type == BaseType.TUPLE:
                    expr_symbol = self._expr_symbol(expr_ctx)
                    if expr_symbol and expr_symbol.tuple_info:
                        element_tuple_info = self._copy_tuple_info(expr_symbol.tuple_info)
        symbol = self.symbols.define_temp(
            resolved_type=BaseType.ARRAY,
            interval=ctx.getSourceInterval(),
        )
        # Track element type from the first element
        if element_type is not None:
            symbol.element_type = element_type
            symbol.tuple_info = element_tuple_info
        return BaseType.ARRAY

    def visitCollectionLiteral(self, ctx: ZincParser.CollectionLiteralContext) -> BaseType:
        """Visit dict/set literal and infer inner types."""
        if not ctx.dictEntry() and not ctx.expression():
            raise ZincTypeError("empty collection literal {} is ambiguous; use dict(), set(), sort_dict(), or sort_set()")

        if ctx.dictEntry():
            key_type = BaseType.UNKNOWN
            value_type = BaseType.UNKNOWN
            for entry_ctx in ctx.dictEntry():
                entry_key_type = self.visit(entry_ctx.expression(0))
                entry_value_type = self.visit(entry_ctx.expression(1))
                key_type = self._merge_key_type(key_type, entry_key_type, "dict key")
                value_type = self._merge_value_type(value_type, entry_value_type, "dict value")

            symbol = self.symbols.define_temp(
                resolved_type=BaseType.DICT,
                interval=ctx.getSourceInterval(),
            )
            symbol.dict_info = DictTypeInfo(
                key_type=key_type,
                value_type=value_type,
                kind="dict",
            )
            return BaseType.DICT

        element_type = BaseType.UNKNOWN
        for expr_ctx in ctx.expression():
            expr_type = self.visit(expr_ctx)
            element_type = self._merge_key_type(element_type, expr_type, "set element")

        symbol = self.symbols.define_temp(
            resolved_type=BaseType.SET,
            interval=ctx.getSourceInterval(),
        )
        symbol.set_info = SetTypeInfo(
            element_type=element_type,
            kind="set",
        )
        return BaseType.SET

    def visitIndexAccessExpr(self, ctx: ZincParser.IndexAccessExprContext) -> BaseType:
        """Visit index access and return element type if array."""
        arr_type = self.visit(ctx.expression(0))
        self.visit(ctx.expression(1))

        # Try to get element type from the array
        element_type = BaseType.UNKNOWN
        tuple_info = None
        if arr_type == BaseType.ARRAY:
            arr_ctx = ctx.expression(0)
            # Look up the array symbol to get element type
            if isinstance(arr_ctx, ZincParser.PrimaryExprContext):
                primary = arr_ctx.primaryExpression()
                if primary and primary.IDENTIFIER():
                    arr_name = primary.IDENTIFIER().getText()
                    arr_symbol = self.symbols.lookup_by_id(arr_name)
                    if arr_symbol and arr_symbol.element_type:
                        element_type = arr_symbol.element_type
                        if element_type == BaseType.TUPLE:
                            tuple_info = self._copy_tuple_info(arr_symbol.tuple_info)
        elif arr_type == BaseType.DICT:
            dict_ctx = ctx.expression(0)
            key_type = self.visit(ctx.expression(1))
            self._merge_key_type(BaseType.UNKNOWN, key_type, "dict key")
            if isinstance(dict_ctx, ZincParser.PrimaryExprContext):
                primary = dict_ctx.primaryExpression()
                if primary and primary.IDENTIFIER():
                    dict_name = primary.IDENTIFIER().getText()
                    dict_symbol = self.symbols.lookup_by_id(dict_name)
                    if dict_symbol and dict_symbol.dict_info:
                        element_type = dict_symbol.dict_info.value_type
            else:
                dict_symbol = self.symbols.lookup_by_interval(
                    dict_ctx.getSourceInterval(), self._current_function
                )
                if dict_symbol and dict_symbol.dict_info:
                    element_type = dict_symbol.dict_info.value_type
        elif arr_type == BaseType.SET:
            raise ZincTypeError("sets do not support index access")
        elif arr_type == BaseType.TUPLE:
            tuple_symbol = self._expr_symbol(ctx.expression(0))
            tuple_info = tuple_symbol.tuple_info if tuple_symbol else None
            index = self._integer_literal_value(ctx.expression(1))
            if index is None:
                raise ZincTypeError("tuple index must be an integer literal")
            if tuple_info is None or index < 0 or index >= len(tuple_info.element_types):
                raise ZincTypeError("tuple index out of bounds")
            element_type = tuple_info.element_types[index]
            symbol = self.symbols.define_temp(
                resolved_type=element_type,
                interval=ctx.getSourceInterval(),
            )
            symbol.tuple_info = self._copy_tuple_info(tuple_info.element_tuple_infos.get(index))
            return element_type

        self.symbols.define_temp(
            resolved_type=element_type,
            interval=ctx.getSourceInterval(),
        ).tuple_info = tuple_info if element_type == BaseType.TUPLE else None
        return element_type

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

        if self._current_module is not None:
            path = extract_identifier_path(ctx)
            if path:
                const_symbol = self.module_graph.resolve_const_path(self._current_module, path)
                if const_symbol:
                    resolved = self.symbols.lookup_by_id(const_symbol.qualified_name)
                    if resolved:
                        self.symbols.define_temp(
                            resolved_type=resolved.resolved_type,
                            interval=ctx.getSourceInterval(),
                        )
                        return resolved.resolved_type

        self.symbols.define_temp(
            resolved_type=BaseType.UNKNOWN,
            interval=ctx.getSourceInterval(),
        )
        return BaseType.UNKNOWN

    def visitFunctionCallExpr(self, ctx: ZincParser.FunctionCallExprContext) -> BaseType:
        """Visit function call expression and create specialization if needed."""
        self.visit(ctx.expression())

        # Collect argument types and array info
        arg_types: list[BaseType] = []
        arg_exprs: list = []
        arg_channel_infos: dict[int, ChannelTypeInfo] = {}
        arg_array_infos: dict[int, ArrayTypeInfo] = {}
        arg_dict_infos: dict[int, DictTypeInfo] = {}
        arg_set_infos: dict[int, SetTypeInfo] = {}
        arg_tuple_infos: dict[int, TupleTypeInfo] = {}
        if ctx.argumentList():
            for i, arg_expr in enumerate(ctx.argumentList().expression()):
                arg_exprs.append(arg_expr)
                arg_type = self.visit(arg_expr)
                if arg_type == BaseType.VOID:
                    raise ZincTypeError("mutating collection methods cannot be used as values")
                arg_types.append(arg_type)

                if arg_type == BaseType.CHANNEL and isinstance(arg_expr, ZincParser.PrimaryExprContext):
                    primary = arg_expr.primaryExpression()
                    if primary and primary.IDENTIFIER():
                        chan_var = primary.IDENTIFIER().getText()
                        if chan_var in self._channel_infos:
                            arg_channel_infos[i] = self._channel_infos[chan_var]
                # Track array element types for array arguments
                elif arg_type == BaseType.ARRAY:
                    arg_symbol = self._expr_symbol(arg_expr)
                    if arg_symbol and arg_symbol.element_type:
                        arg_array_infos[i] = ArrayTypeInfo(
                            element_type=arg_symbol.element_type,
                            element_tuple_info=self._copy_tuple_info(arg_symbol.tuple_info),
                        )
                    elif isinstance(arg_expr, ZincParser.PrimaryExprContext):
                        primary = arg_expr.primaryExpression()
                        if primary and primary.IDENTIFIER():
                            arr_var = primary.IDENTIFIER().getText()
                            arr_symbol = self.symbols.lookup_by_id(arr_var)
                            if arr_symbol and arr_symbol.element_type:
                                arg_array_infos[i] = ArrayTypeInfo(
                                    element_type=arr_symbol.element_type,
                                    element_tuple_info=self._copy_tuple_info(arr_symbol.tuple_info),
                                )
                elif arg_type == BaseType.DICT:
                    arg_symbol = self.symbols.lookup_by_interval(
                        arg_expr.getSourceInterval(), self._current_function
                    )
                    if arg_symbol and arg_symbol.dict_info:
                        arg_dict_infos[i] = self._copy_dict_info(arg_symbol.dict_info) or DictTypeInfo()
                    elif isinstance(arg_expr, ZincParser.PrimaryExprContext):
                        primary = arg_expr.primaryExpression()
                        if primary and primary.IDENTIFIER():
                            dict_symbol = self.symbols.lookup_by_id(primary.IDENTIFIER().getText())
                            if dict_symbol and dict_symbol.dict_info:
                                arg_dict_infos[i] = self._copy_dict_info(dict_symbol.dict_info) or DictTypeInfo()
                elif arg_type == BaseType.SET:
                    arg_symbol = self.symbols.lookup_by_interval(
                        arg_expr.getSourceInterval(), self._current_function
                    )
                    if arg_symbol and arg_symbol.set_info:
                        arg_set_infos[i] = self._copy_set_info(arg_symbol.set_info) or SetTypeInfo()
                    elif isinstance(arg_expr, ZincParser.PrimaryExprContext):
                        primary = arg_expr.primaryExpression()
                        if primary and primary.IDENTIFIER():
                            set_symbol = self.symbols.lookup_by_id(primary.IDENTIFIER().getText())
                            if set_symbol and set_symbol.set_info:
                                arg_set_infos[i] = self._copy_set_info(set_symbol.set_info) or SetTypeInfo()
                elif arg_type == BaseType.TUPLE:
                    arg_symbol = self._expr_symbol(arg_expr)
                    if arg_symbol and arg_symbol.tuple_info:
                        copied = self._copy_tuple_info(arg_symbol.tuple_info)
                        if copied:
                            arg_tuple_infos[i] = copied

        callee_ctx = ctx.expression()

        if isinstance(callee_ctx, ZincParser.PrimaryExprContext):
            primary = callee_ctx.primaryExpression()
            if primary and primary.IDENTIFIER():
                func_name = primary.IDENTIFIER().getText()
                if func_name == "chan":
                    if len(arg_types) > 1:
                        raise ZincTypeError("chan() accepts at most one capacity argument")
                    if arg_types and arg_types[0] != BaseType.INTEGER:
                        raise ZincTypeError("chan() capacity must be an integer")
                    self.symbols.define_temp(
                        resolved_type=BaseType.CHANNEL,
                        interval=ctx.getSourceInterval(),
                    )
                    return BaseType.CHANNEL
                if func_name in {"dict", "sort_dict"}:
                    if arg_types:
                        raise ZincTypeError(f"{func_name}() does not accept arguments")
                    symbol = self.symbols.define_temp(
                        resolved_type=BaseType.DICT,
                        interval=ctx.getSourceInterval(),
                    )
                    symbol.dict_info = DictTypeInfo(kind=func_name)
                    return BaseType.DICT
                if func_name in {"set", "sort_set"}:
                    if arg_types:
                        raise ZincTypeError(f"{func_name}() does not accept arguments")
                    symbol = self.symbols.define_temp(
                        resolved_type=BaseType.SET,
                        interval=ctx.getSourceInterval(),
                    )
                    symbol.set_info = SetTypeInfo(kind=func_name)
                    return BaseType.SET

        # Check for method call (e.g., b.push(10))
        if isinstance(callee_ctx, ZincParser.MemberAccessExprContext):
            method_name = callee_ctx.IDENTIFIER().getText()
            receiver_ctx = callee_ctx.expression()

            # len() always returns an integer (usize in Rust, i64 in Zinc)
            if method_name == "len":
                self.symbols.define_temp(
                    resolved_type=BaseType.INTEGER,
                    interval=ctx.getSourceInterval(),
                )
                return BaseType.INTEGER

            if method_name in {"is_empty", "contains", "contains_key"}:
                self.symbols.define_temp(
                    resolved_type=BaseType.BOOLEAN,
                    interval=ctx.getSourceInterval(),
                )
                return BaseType.BOOLEAN

            # Get the receiver variable name if it's a simple identifier
            if isinstance(receiver_ctx, ZincParser.PrimaryExprContext):
                primary = receiver_ctx.primaryExpression()
                if primary and primary.IDENTIFIER():
                    var_name = primary.IDENTIFIER().getText()
                    var_symbol = self.symbols.lookup_by_id(var_name)
                    if var_symbol:
                        # Check if this method mutates the receiver
                        if is_mutating_method(var_symbol.resolved_type, method_name):
                            if var_symbol.resolved_type == BaseType.DICT and self._is_iterating_dict(var_name):
                                raise ZincTypeError("cannot mutate dict during iteration")
                            var_symbol.is_mutated = True

                        # For push on arrays, track element type
                        if (
                            method_name == "push"
                            and var_symbol.resolved_type == BaseType.ARRAY
                            and arg_types
                        ):
                            if var_symbol.element_type is None:
                                var_symbol.element_type = arg_types[0]
                            if arg_types[0] == BaseType.TUPLE:
                                arg_symbol = self._expr_symbol(arg_exprs[0])
                                if arg_symbol and arg_symbol.tuple_info:
                                    var_symbol.tuple_info = self._copy_tuple_info(arg_symbol.tuple_info)

                        if var_symbol.resolved_type == BaseType.DICT and var_symbol.dict_info:
                            dict_info = var_symbol.dict_info
                            if method_name == "insert":
                                if len(arg_types) != 2:
                                    raise ZincTypeError("dict.insert() expects key and value arguments")
                                dict_info.key_type = self._merge_key_type(dict_info.key_type, arg_types[0], "dict key")
                                dict_info.value_type = self._merge_value_type(
                                    dict_info.value_type, arg_types[1], "dict value"
                                )
                            elif method_name in {"get", "contains_key", "remove"}:
                                if len(arg_types) != 1:
                                    raise ZincTypeError(f"dict.{method_name}() expects one key argument")
                                dict_info.key_type = self._merge_key_type(dict_info.key_type, arg_types[0], "dict key")
                            elif method_name == "clear":
                                if arg_types:
                                    raise ZincTypeError("dict.clear() does not accept arguments")
                            elif method_name == "keys":
                                if arg_types:
                                    raise ZincTypeError("dict.keys() does not accept arguments")
                                symbol = self.symbols.define_temp(
                                    resolved_type=BaseType.ARRAY,
                                    interval=ctx.getSourceInterval(),
                                )
                                symbol.element_type = dict_info.key_type
                                return BaseType.ARRAY
                            elif method_name == "values":
                                if arg_types:
                                    raise ZincTypeError("dict.values() does not accept arguments")
                                symbol = self.symbols.define_temp(
                                    resolved_type=BaseType.ARRAY,
                                    interval=ctx.getSourceInterval(),
                                )
                                symbol.element_type = dict_info.value_type
                                return BaseType.ARRAY
                            elif method_name == "items":
                                if arg_types:
                                    raise ZincTypeError("dict.items() does not accept arguments")
                                symbol = self.symbols.define_temp(
                                    resolved_type=BaseType.ARRAY,
                                    interval=ctx.getSourceInterval(),
                                )
                                symbol.element_type = BaseType.TUPLE
                                symbol.tuple_info = self._tuple_info_from_dict_info(dict_info)
                                return BaseType.ARRAY

                            if method_name == "get":
                                self.symbols.define_temp(
                                    resolved_type=dict_info.value_type,
                                    interval=ctx.getSourceInterval(),
                                )
                                return dict_info.value_type
                            if method_name in {"insert", "remove", "clear"}:
                                self.symbols.define_temp(
                                    resolved_type=BaseType.VOID,
                                    interval=ctx.getSourceInterval(),
                                )
                                return BaseType.VOID

                        if var_symbol.resolved_type == BaseType.SET and var_symbol.set_info:
                            set_info = var_symbol.set_info
                            if method_name in {"push", "insert", "contains", "remove"}:
                                if len(arg_types) != 1:
                                    raise ZincTypeError(f"set.{method_name}() expects one element argument")
                                set_info.element_type = self._merge_key_type(
                                    set_info.element_type, arg_types[0], "set element"
                                )
                            elif method_name == "clear":
                                if arg_types:
                                    raise ZincTypeError("set.clear() does not accept arguments")

                            if method_name in {"push", "insert", "remove", "clear"}:
                                self.symbols.define_temp(
                                    resolved_type=BaseType.VOID,
                                    interval=ctx.getSourceInterval(),
                                )
                                return BaseType.VOID

        path = extract_identifier_path(callee_ctx)
        if path and self._current_module is not None:
            static_target = self.module_graph.resolve_static_method_target(self._current_module, path)
            if static_target:
                struct_symbol, method_name = static_target
                struct = self.atlas.structs.get(struct_symbol.qualified_name)
                if struct:
                    method = next((candidate for candidate in struct.methods if candidate.name == method_name), None)
                    if method:
                        return_type = self._method_return_base_type(method.return_type)
                        temp = self.symbols.define_temp(
                            resolved_type=return_type,
                            interval=ctx.getSourceInterval(),
                        )
                        if return_type == BaseType.STRUCT:
                            temp.tuple_info = None
                        return return_type

            resolved_function = self.module_graph.resolve_function_path(self._current_module, path)
            if resolved_function and resolved_function.name not in ("print", "chan", "dict", "sort_dict", "set", "sort_set"):
                func_def = self.atlas.function_defs.get(resolved_function.qualified_name)
                if func_def and BaseType.UNKNOWN not in arg_types:
                    mangled = self.atlas.add_specialization(
                        resolved_function.qualified_name,
                        arg_types,
                        func_def,
                        self._current_function,
                        arg_channel_infos,
                        arg_array_infos,
                        arg_dict_infos,
                        arg_set_infos,
                        arg_tuple_infos,
                    )
                    key = (self._current_function, ctx.getSourceInterval())
                    self.specialization_map[key] = mangled

                    func_instance = self.atlas.functions.get(mangled)
                    if func_instance:
                        for idx, chan_info in arg_channel_infos.items():
                            func_instance.arg_channel_infos.setdefault(idx, [])
                            if all(existing is not chan_info for existing in func_instance.arg_channel_infos[idx]):
                                func_instance.arg_channel_infos[idx].append(chan_info)
                        self._mark_mutated_call_arguments(func_instance, arg_exprs)
                    if func_instance and func_instance.return_type != BaseType.VOID:
                        temp = self.symbols.define_temp(
                            resolved_type=func_instance.return_type,
                            interval=ctx.getSourceInterval(),
                        )
                        temp.dict_info = self._copy_dict_info(func_instance.return_dict_info)
                        temp.set_info = self._copy_set_info(func_instance.return_set_info)
                        temp.tuple_info = self._copy_tuple_info(func_instance.return_tuple_info)
                        return func_instance.return_type

            if len(path) == 1:
                func_symbol = self.symbols.lookup_by_id(path[0])
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

    def _mark_mutated_call_arguments(self, func_instance: FunctionInstance, arg_exprs: list) -> None:
        """Mark caller variables as mutable when callee parameters are inferred mutable."""
        for i, arg_expr in enumerate(arg_exprs):
            is_mutated = False
            if i in func_instance.arg_array_infos and func_instance.arg_array_infos[i].is_mutated:
                is_mutated = True
            if i in func_instance.arg_dict_infos and func_instance.arg_dict_infos[i].is_mutated:
                is_mutated = True
            if i in func_instance.arg_set_infos and func_instance.arg_set_infos[i].is_mutated:
                is_mutated = True
            if not is_mutated:
                continue
            if isinstance(arg_expr, ZincParser.PrimaryExprContext):
                primary = arg_expr.primaryExpression()
                if primary and primary.IDENTIFIER():
                    symbol = self.symbols.lookup_by_id(primary.IDENTIFIER().getText())
                    if symbol:
                        symbol.is_mutated = True

    def visitStructInstantiation(self, ctx: ZincParser.StructInstantiationContext) -> BaseType:
        """Visit struct literal."""
        for field_ctx in ctx.fieldInit():
            self.visit(field_ctx.expression())

        if self._current_module is not None:
            resolved_struct = self.module_graph.resolve_struct_path(
                self._current_module, struct_path_from_ctx(ctx)
            )
            if resolved_struct is None:
                raise ZincTypeError(f"unknown struct '{ctx.qualifiedName().getText()}'")
        self.symbols.define_temp(
            resolved_type=BaseType.STRUCT,
            interval=ctx.getSourceInterval(),
        )
        return BaseType.STRUCT

    def visitVariableAssignment(self, ctx: ZincParser.VariableAssignmentContext) -> None:
        """Visit variable assignment with shadowing support."""
        expr_type = self.visit(ctx.expression())
        if expr_type == BaseType.VOID:
            raise ZincTypeError("mutating collection methods cannot be used as assignment values")
        target = ctx.assignmentTarget()

        if target.IDENTIFIER():
            var_name = target.IDENTIFIER().getText()
            existing = self.symbols.lookup_by_id(var_name)

            # Check if this is a chan() call - track channel info
            if expr_type == BaseType.CHANNEL and self._is_channel_constructor_call(ctx.expression()):
                existing_chan = self._channel_infos.get(var_name)
                is_bounded = bool(ctx.expression().argumentList())
                if existing_chan is None:
                    self._channel_infos[var_name] = ChannelTypeInfo(
                        element_type=BaseType.UNKNOWN,
                        is_bounded=is_bounded,
                    )
                else:
                    existing_chan.is_bounded = is_bounded

            # Get element type from expression if it's an array
            expr_element_type = None
            if expr_type == BaseType.ARRAY:
                expr_symbol = self.symbols.lookup_by_interval(
                    ctx.expression().getSourceInterval(), self._current_function
                )
                if expr_symbol and expr_symbol.element_type:
                    expr_element_type = expr_symbol.element_type

            expr_dict_info = None
            if expr_type == BaseType.DICT:
                expr_symbol = self.symbols.lookup_by_interval(
                    ctx.expression().getSourceInterval(), self._current_function
                )
                if expr_symbol and expr_symbol.dict_info:
                    expr_dict_info = self._copy_dict_info(expr_symbol.dict_info)

            expr_set_info = None
            if expr_type == BaseType.SET:
                expr_symbol = self.symbols.lookup_by_interval(
                    ctx.expression().getSourceInterval(), self._current_function
                )
                if expr_symbol and expr_symbol.set_info:
                    expr_set_info = self._copy_set_info(expr_symbol.set_info)

            expr_tuple_info = None
            expr_symbol = self.symbols.lookup_by_interval(
                ctx.expression().getSourceInterval(), self._current_function
            )
            if expr_symbol and expr_symbol.tuple_info:
                expr_tuple_info = self._copy_tuple_info(expr_symbol.tuple_info)

            if existing is None:
                # First assignment - create new symbol
                new_sym = self.symbols.define(
                    id=var_name,
                    kind=SymbolKind.VARIABLE,
                    resolved_type=expr_type,
                    interval=target.getSourceInterval(),
                    is_shadow=False,
                )
                # Propagate array element type
                if expr_element_type:
                    new_sym.element_type = expr_element_type
                if expr_dict_info:
                    new_sym.dict_info = expr_dict_info
                if expr_set_info:
                    new_sym.set_info = expr_set_info
                if expr_tuple_info:
                    new_sym.tuple_info = expr_tuple_info
            elif existing.resolved_type != expr_type:
                # Type change - create shadow symbol
                new_sym = self.symbols.define(
                    id=var_name,
                    kind=SymbolKind.VARIABLE,
                    resolved_type=expr_type,
                    interval=target.getSourceInterval(),
                    is_shadow=True,
                )
                if expr_element_type:
                    new_sym.element_type = expr_element_type
                if expr_dict_info:
                    new_sym.dict_info = expr_dict_info
                if expr_set_info:
                    new_sym.set_info = expr_set_info
                if expr_tuple_info:
                    new_sym.tuple_info = expr_tuple_info
            elif expr_type == BaseType.DICT:
                if expr_dict_info:
                    if existing.dict_info is None:
                        existing.dict_info = expr_dict_info
                    elif existing.dict_info.kind != expr_dict_info.kind:
                        new_sym = self.symbols.define(
                            id=var_name,
                            kind=SymbolKind.VARIABLE,
                            resolved_type=expr_type,
                            interval=target.getSourceInterval(),
                            is_shadow=True,
                        )
                        new_sym.dict_info = expr_dict_info
                        return
                    else:
                        try:
                            existing.dict_info.key_type = self._merge_key_type(
                                existing.dict_info.key_type, expr_dict_info.key_type, "dict key"
                            )
                            existing.dict_info.value_type = self._merge_value_type(
                                existing.dict_info.value_type, expr_dict_info.value_type, "dict value"
                            )
                        except ZincTypeError:
                            new_sym = self.symbols.define(
                                id=var_name,
                                kind=SymbolKind.VARIABLE,
                                resolved_type=expr_type,
                                interval=target.getSourceInterval(),
                                is_shadow=True,
                            )
                            new_sym.dict_info = expr_dict_info
                            return
                existing.is_mutated = True
                self.symbols.define_temp(
                    resolved_type=expr_type,
                    interval=target.getSourceInterval(),
                )
            elif expr_type == BaseType.SET:
                if expr_set_info:
                    if existing.set_info is None:
                        existing.set_info = expr_set_info
                    elif existing.set_info.kind != expr_set_info.kind:
                        new_sym = self.symbols.define(
                            id=var_name,
                            kind=SymbolKind.VARIABLE,
                            resolved_type=expr_type,
                            interval=target.getSourceInterval(),
                            is_shadow=True,
                        )
                        new_sym.set_info = expr_set_info
                        return
                    else:
                        try:
                            existing.set_info.element_type = self._merge_key_type(
                                existing.set_info.element_type, expr_set_info.element_type, "set element"
                            )
                        except ZincTypeError:
                            new_sym = self.symbols.define(
                                id=var_name,
                                kind=SymbolKind.VARIABLE,
                                resolved_type=expr_type,
                                interval=target.getSourceInterval(),
                                is_shadow=True,
                            )
                            new_sym.set_info = expr_set_info
                            return
                existing.is_mutated = True
                self.symbols.define_temp(
                    resolved_type=expr_type,
                    interval=target.getSourceInterval(),
                )
            elif expr_type == BaseType.TUPLE:
                if expr_tuple_info:
                    existing.tuple_info = expr_tuple_info
                existing.is_mutated = True
                self.symbols.define_temp(
                    resolved_type=expr_type,
                    interval=target.getSourceInterval(),
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
        elif target.tupleAssignmentTarget():
            expr_symbol = self._expr_symbol(ctx.expression())
            tuple_info = expr_symbol.tuple_info if expr_symbol else None
            if expr_type != BaseType.TUPLE or tuple_info is None:
                if expr_type == BaseType.UNKNOWN:
                    for token in self._binding_tokens(target.tupleAssignmentTarget()):
                        self.symbols.define(
                            id=token.getText(),
                            kind=SymbolKind.VARIABLE,
                            resolved_type=BaseType.UNKNOWN,
                            interval=token.getSourceInterval(),
                        )
                    return
                raise ZincTypeError("tuple destructuring assignment requires a tuple value")

            tokens = self._binding_tokens(target.tupleAssignmentTarget())
            if len(tokens) != len(tuple_info.element_types):
                raise ZincTypeError("tuple destructuring arity mismatch")

            for i, token in enumerate(tokens):
                var_name = token.getText()
                element_type = tuple_info.element_types[i]
                existing = self.symbols.lookup_by_id(var_name)
                new_tuple_info = self._copy_tuple_info(tuple_info.element_tuple_infos.get(i))
                if existing is None or existing.resolved_type != element_type:
                    new_sym = self.symbols.define(
                        id=var_name,
                        kind=SymbolKind.VARIABLE,
                        resolved_type=element_type,
                        interval=token.getSourceInterval(),
                        is_shadow=existing is not None,
                    )
                    new_sym.tuple_info = new_tuple_info
                else:
                    existing.is_mutated = True
                    if new_tuple_info:
                        existing.tuple_info = new_tuple_info
                    temp = self.symbols.define_temp(
                        resolved_type=element_type,
                        interval=token.getSourceInterval(),
                    )
                    temp.tuple_info = new_tuple_info
        elif target.indexAccess():
            index_access = target.indexAccess()
            collection_ctx = index_access.expression(0)
            key_ctx = index_access.expression(1)
            collection_type = self.visit(collection_ctx)
            key_type = self.visit(key_ctx)
            if collection_type != BaseType.DICT:
                self.symbols.define_temp(
                    resolved_type=expr_type,
                    interval=target.getSourceInterval(),
                )
                return

            if isinstance(collection_ctx, ZincParser.PrimaryExprContext):
                primary = collection_ctx.primaryExpression()
                if primary and primary.IDENTIFIER():
                    var_name = primary.IDENTIFIER().getText()
                    if self._is_iterating_dict(var_name):
                        raise ZincTypeError("cannot mutate dict during iteration")
                    var_symbol = self.symbols.lookup_by_id(var_name)
                    if var_symbol and var_symbol.dict_info:
                        var_symbol.is_mutated = True
                        var_symbol.dict_info.key_type = self._merge_key_type(
                            var_symbol.dict_info.key_type, key_type, "dict key"
                        )
                        var_symbol.dict_info.value_type = self._merge_value_type(
                            var_symbol.dict_info.value_type, expr_type, "dict value"
                        )
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
            expr_symbol = self.symbols.lookup_by_interval(
                ctx.expression().getSourceInterval(), self._current_function
            )
            if return_type == BaseType.DICT and expr_symbol:
                self._current_return_dict_info = self._merge_dict_info(
                    self._current_return_dict_info, expr_symbol.dict_info
                )
            if return_type == BaseType.SET and expr_symbol:
                self._current_return_set_info = self._merge_set_info(
                    self._current_return_set_info, expr_symbol.set_info
                )
            if return_type == BaseType.TUPLE and expr_symbol:
                self._current_return_tuple_info = self._merge_tuple_info(
                    self._current_return_tuple_info, expr_symbol.tuple_info
                )
            if self._current_return_type == BaseType.VOID:
                self._current_return_type = return_type
            elif return_type != BaseType.UNKNOWN and return_type != self._current_return_type:
                # Promote int+float -> float when return paths disagree
                if {self._current_return_type, return_type} == {BaseType.INTEGER, BaseType.FLOAT}:
                    self._current_return_type = BaseType.FLOAT

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
        expr_symbol = self._expr_symbol(ctx.expression())

        block_name = self._next_block_name("for")
        self.symbols.enter_scope(block_name)

        binding = ctx.forBinding()
        binding_ctx = binding.tupleAssignmentTarget() or binding
        tokens = self._binding_tokens(binding_ctx)

        def define_binding(index: int, resolved_type: BaseType, tuple_info: TupleTypeInfo | None = None) -> None:
            token = tokens[index]
            symbol = self.symbols.define(
                id=token.getText(),
                kind=SymbolKind.VARIABLE,
                resolved_type=resolved_type,
                interval=token.getSourceInterval(),
            )
            symbol.tuple_info = self._copy_tuple_info(tuple_info)

        item_tuple_info: TupleTypeInfo | None = None
        if iterable_type == BaseType.INTEGER:
            var_type = BaseType.INTEGER
        elif iterable_type == BaseType.ARRAY:
            var_type = BaseType.UNKNOWN
            if expr_symbol and expr_symbol.element_type:
                var_type = expr_symbol.element_type
                if var_type == BaseType.TUPLE:
                    item_tuple_info = expr_symbol.tuple_info
        elif iterable_type == BaseType.SET:
            var_type = BaseType.UNKNOWN
            if expr_symbol and expr_symbol.set_info:
                var_type = expr_symbol.set_info.element_type
        elif iterable_type == BaseType.DICT:
            var_type = BaseType.TUPLE
            if expr_symbol and expr_symbol.dict_info:
                item_tuple_info = self._tuple_info_from_dict_info(expr_symbol.dict_info)
        else:
            var_type = BaseType.UNKNOWN

        if len(tokens) == 1:
            define_binding(0, var_type, item_tuple_info)
        else:
            if var_type != BaseType.TUPLE or item_tuple_info is None:
                raise ZincTypeError("for-loop destructuring requires tuple items")
            if len(tokens) != len(item_tuple_info.element_types):
                raise ZincTypeError("for-loop destructuring arity mismatch")
            for i, element_type in enumerate(item_tuple_info.element_types):
                define_binding(i, element_type, item_tuple_info.element_tuple_infos.get(i))

        iterated_dict_name = self._iterated_dict_name(ctx.expression())
        self._iterating_dict_stack.append({iterated_dict_name} if iterated_dict_name else set())
        try:
            self.visit(ctx.block())
        finally:
            self._iterating_dict_stack.pop()
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

    def visitSelectStatement(self, ctx: ZincParser.SelectStatementContext) -> None:
        """Visit a select statement and validate case structure."""
        default_count = sum(
            isinstance(case_ctx, ZincParser.SelectDefaultCaseContext)
            for case_ctx in ctx.selectCase()
        )
        if default_count > 1:
            raise ZincTypeError("select supports at most one default case")
        for case_ctx in ctx.selectCase():
            self.visit(case_ctx)

    def visitSelectReceiveCase(self, ctx: ZincParser.SelectReceiveCaseContext) -> None:
        """Visit a select receive case."""
        binding_name = ctx.IDENTIFIER(0).getText()
        channel_name = ctx.IDENTIFIER(1).getText()
        channel_symbol = self.symbols.lookup_by_id(channel_name)
        if channel_symbol is None or channel_symbol.resolved_type != BaseType.CHANNEL:
            raise ZincTypeError(f"'{channel_name}' is not a channel")
        if channel_symbol.kind == SymbolKind.PARAMETER:
            raise ZincTypeError("cannot receive from channel parameter")

        block_name = self._next_block_name("select")
        self.symbols.enter_scope(block_name)
        try:
            channel_info = self._channel_info_for_name(channel_name)
            self.symbols.define(
                id=binding_name,
                kind=SymbolKind.VARIABLE,
                resolved_type=channel_info.element_type,
                interval=ctx.IDENTIFIER(0).getSourceInterval(),
                is_shadow=self.symbols.lookup_by_id(binding_name) is not None,
            )
            self.visit(ctx.block())
        finally:
            self.symbols.exit_scope()

    def visitSelectSendCase(self, ctx: ZincParser.SelectSendCaseContext) -> None:
        """Visit a select send case."""
        channel_name = ctx.IDENTIFIER().getText()
        value_type = self.visit(ctx.expression())
        self._merge_channel_value_type(channel_name, value_type)

        block_name = self._next_block_name("select")
        self.symbols.enter_scope(block_name)
        try:
            self.visit(ctx.block())
        finally:
            self.symbols.exit_scope()

    def visitSelectDefaultCase(self, ctx: ZincParser.SelectDefaultCaseContext) -> None:
        """Visit a select default case."""
        block_name = self._next_block_name("select")
        self.symbols.enter_scope(block_name)
        try:
            self.visit(ctx.block())
        finally:
            self.symbols.exit_scope()

    def visitSpawnStatement(self, ctx: ZincParser.SpawnStatementContext) -> None:
        """Visit spawn statement and create specialization for spawned function."""
        func_expr = ctx.expression()
        path = extract_identifier_path(func_expr)
        if path is None or self._current_module is None:
            return

        # Collect argument types and track channel arguments
        arg_types: list[BaseType] = []
        arg_channel_infos: dict[int, ChannelTypeInfo] = {}
        if ctx.argumentList():
            for i, arg_expr in enumerate(ctx.argumentList().expression()):
                arg_type = self.visit(arg_expr)
                arg_types.append(arg_type)

                if arg_type == BaseType.CHANNEL and isinstance(arg_expr, ZincParser.PrimaryExprContext):
                    arg_primary = arg_expr.primaryExpression()
                    if arg_primary and arg_primary.IDENTIFIER():
                        chan_var = arg_primary.IDENTIFIER().getText()
                        if chan_var in self._channel_infos:
                            arg_channel_infos[i] = self._channel_infos[chan_var]

        resolved_function = self.module_graph.resolve_function_path(self._current_module, path)
        if resolved_function is None or resolved_function.name in ("print", "chan"):
            return

        func_def = self.atlas.function_defs.get(resolved_function.qualified_name)
        if func_def is None or BaseType.UNKNOWN in arg_types:
            return

        mangled = self.atlas.add_specialization(
            resolved_function.qualified_name,
            arg_types,
            func_def,
            self._current_function,
            arg_channel_infos,
        )
        key = (self._current_function, ctx.getSourceInterval())
        self.specialization_map[key] = mangled
        self.atlas.functions[mangled].is_async = True
        for idx, chan_info in arg_channel_infos.items():
            self.atlas.functions[mangled].arg_channel_infos.setdefault(idx, [])
            if all(
                existing is not chan_info
                for existing in self.atlas.functions[mangled].arg_channel_infos[idx]
            ):
                self.atlas.functions[mangled].arg_channel_infos[idx].append(chan_info)

    def visitChannelSendStatement(self, ctx: ZincParser.ChannelSendStatementContext) -> None:
        """Visit channel send statement and infer channel element type."""
        channel_name = ctx.IDENTIFIER().getText()
        value_type = self.visit(ctx.expression())
        self._merge_channel_value_type(channel_name, value_type)

    def visitChannelReceiveExpr(self, ctx: ZincParser.ChannelReceiveExprContext) -> BaseType:
        """Visit channel receive expression."""
        chan_expr = ctx.expression()
        expr_type = self.visit(chan_expr)

        if isinstance(chan_expr, ZincParser.PrimaryExprContext):
            primary = chan_expr.primaryExpression()
            if primary and primary.IDENTIFIER():
                channel_name = primary.IDENTIFIER().getText()
                channel_symbol = self.symbols.lookup_by_id(channel_name)
                if channel_symbol is None or channel_symbol.resolved_type != BaseType.CHANNEL:
                    raise ZincTypeError(f"'{channel_name}' is not a channel")
                if channel_symbol.kind == SymbolKind.PARAMETER:
                    raise ZincTypeError("cannot receive from channel parameter")
                elem_type = self._channel_info_for_name(channel_name).element_type
                self.symbols.define_temp(
                    resolved_type=elem_type,
                    interval=ctx.getSourceInterval(),
                )
                return elem_type

        if expr_type != BaseType.CHANNEL:
            raise ZincTypeError("channel receive expects a channel expression")

        self.symbols.define_temp(
            resolved_type=BaseType.UNKNOWN,
            interval=ctx.getSourceInterval(),
        )
        return BaseType.UNKNOWN
