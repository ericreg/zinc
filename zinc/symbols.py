"""Symbol Table for the Zinc compiler."""

import re
from dataclasses import dataclass, replace
from enum import Enum, auto

from antlr4 import ParserRuleContext

from zinc.ast.types import (
    AnonymousStructFieldInfo,
    AnonymousStructTypeInfo,
    BaseType,
    TypeInfo,
    default_exact_type,
    exact_type_to_base,
    exact_type_to_rust,
    normalize_exact_type,
    promote_exact_numeric,
    parse_literal,
    is_mutating_method,
    type_to_rust,
    promote_numeric,
    CallableTarget,
    CallableTypeInfo,
    ChannelTypeInfo,
    ArrayTypeInfo,
    DictTypeInfo,
    SetTypeInfo,
    TupleTypeInfo,
    value_type_key,
)
from zinc.exceptions import ZincTypeError
from zinc.parser.zincVisitor import zincVisitor
from zinc.parser.zincParser import zincParser as ZincParser
from zinc.atlas import (
    Atlas,
    ConstInstance,
    EnumInstance,
    EnumVariantInfo,
    FunctionInstance,
    StructFieldInfo,
    StructInstance,
    StructMethodInfo,
)
from zinc.modules import (
    enum_variant_path_from_ctx,
    extract_identifier_path,
    struct_composition_from_ctx,
    struct_path_from_ctx,
)
from zinc.meta_runtime import (
    BUILTIN_META_QNAME,
    COMPONENT_ORDER_QNAME,
    COMPONENT_ORDER_VARIANTS,
    CONST_META_QNAME,
    ENUM_META_QNAME,
    FIELD_META_QNAME,
    FUNCTION_META_QNAME,
    FUNCTION_PARAM_META_QNAME,
    METHOD_META_QNAME,
    METHOD_PARAM_META_QNAME,
    MetaListValue,
    MetaValue,
    STRUCT_META_QNAME,
    TYPE_META_QNAME,
    VARIABLE_META_QNAME,
    VARIANT_META_QNAME,
    component_order_value,
    is_meta_struct_qname,
    unknown_type_meta,
)


class SymbolKind(Enum):
    """Kind of symbol in the symbol table."""

    VARIABLE = auto()  # Local variable
    PARAMETER = auto()  # Function parameter
    CONST = auto()  # Global constant
    TEMPORARY = auto()  # Intermediate expression result
    FUNCTION = auto()  # User-defined function
    BUILTIN = auto()  # Built-in function (print, chan, etc.)
    STRUCT = auto()  # Struct type
    ENUM = auto()  # Enum type
    LITERAL = auto()  # Literal value


@dataclass
class Symbol:
    """A symbol in the symbol table."""

    id: str | None  # Original name (None for temporaries/literals)
    unique_name: str  # Scoped unique name with type (e.g., "main.a/i64", "tmp_0")
    kind: SymbolKind
    resolved_type: BaseType
    source_interval: tuple[int, int]  # ANTLR source interval (start, stop)
    exact_type: str | None = None
    declared_exact_type: str | None = None
    has_declared_type: bool = False
    is_mutated: bool = False  # True if variable needs 'mut' (reassigned or mutating method called)
    is_shadow: bool = False  # True if this shadows a previous binding of the same name
    element_type: BaseType | None = None  # For arrays: type of elements
    element_exact_type: str | None = None
    channel_info: ChannelTypeInfo | None = None
    dict_info: DictTypeInfo | None = None
    set_info: SetTypeInfo | None = None
    tuple_info: TupleTypeInfo | None = None
    callable_info: CallableTypeInfo | None = None
    anonymous_struct_info: AnonymousStructTypeInfo | None = None
    element_struct_qualified_name: str | None = None
    element_anonymous_struct_info: AnonymousStructTypeInfo | None = None
    binding_unique_name: str | None = None  # For temps/captured refs: the underlying binding
    is_captured_binding: bool = False  # True when this binding is shared with one or more closures
    is_captured_ref: bool = False  # True for closure-local aliases of captured outer bindings
    constant_value: object | None = None
    line_num: int = 0


@dataclass
class CaptureBindingInfo:
    """Metadata for one captured outer binding."""

    name: str
    binding_unique_name: str
    resolved_type: BaseType
    exact_type: str | None = None
    declared_exact_type: str | None = None
    has_declared_type: bool = False
    channel_info: ChannelTypeInfo | None = None
    element_type: BaseType | None = None
    element_exact_type: str | None = None
    dict_info: DictTypeInfo | None = None
    set_info: SetTypeInfo | None = None
    tuple_info: TupleTypeInfo | None = None
    callable_info: CallableTypeInfo | None = None
    struct_qualified_name: str | None = None
    anonymous_struct_info: AnonymousStructTypeInfo | None = None
    element_struct_qualified_name: str | None = None
    element_anonymous_struct_info: AnonymousStructTypeInfo | None = None


@dataclass
class LexicalFunctionInfo:
    """A nested function or lambda defined within another function specialization."""

    name: str
    qualified_name: str
    owner_function: str
    module_id: str
    ctx: ParserRuleContext
    is_async: bool
    display_name: str
    captures: list[CaptureBindingInfo] = None  # type: ignore[assignment]
    finalized: bool = False

    def __post_init__(self) -> None:
        if self.captures is None:
            self.captures = []


@dataclass
class ResolvedValueInfo:
    """Resolved type plus rich metadata for a value-producing expression."""

    base_type: BaseType
    exact_type: str | None = None
    array_info: ArrayTypeInfo | None = None
    channel_info: ChannelTypeInfo | None = None
    dict_info: DictTypeInfo | None = None
    set_info: SetTypeInfo | None = None
    tuple_info: TupleTypeInfo | None = None
    callable_info: CallableTypeInfo | None = None
    struct_qualified_name: str | None = None
    anonymous_struct_info: AnonymousStructTypeInfo | None = None


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
        exact_type: str | None = None,
        declared_exact_type: str | None = None,
        has_declared_type: bool = False,
        is_shadow: bool = False,
        constant_value: object | None = None,
        line_num: int = 0,
    ) -> Symbol:
        """Define a named symbol in current scope."""
        # Include type in unique_name for shadowing support
        type_suffix = exact_type_to_rust(exact_type, resolved_type)
        base_name = f"{self.current_scope}.{id}" if self._scope_path else id
        unique_name = f"{base_name}/{type_suffix}"

        symbol = Symbol(
            id=id,
            unique_name=unique_name,
            kind=kind,
            resolved_type=resolved_type,
            exact_type=exact_type,
            declared_exact_type=declared_exact_type,
            has_declared_type=has_declared_type,
            source_interval=interval,
            is_shadow=is_shadow,
            constant_value=constant_value,
            line_num=line_num,
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
        exact_type: str | None = None,
        kind: SymbolKind = SymbolKind.TEMPORARY,
        constant_value: object | None = None,
        line_num: int = 0,
    ) -> Symbol:
        """Define a temporary symbol for an expression."""
        unique_name = f"tmp_{self._temp_counter}"
        self._temp_counter += 1
        symbol = Symbol(
            id=None,
            unique_name=unique_name,
            kind=kind,
            resolved_type=resolved_type,
            exact_type=exact_type,
            source_interval=interval,
            constant_value=constant_value,
            line_num=line_num,
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

    def lookup_by_unique_name(self, unique_name: str) -> Symbol | None:
        """Look up the symbol with this scoped unique name."""
        for symbol in reversed(self._symbols):
            if symbol.unique_name == unique_name:
                return symbol
        return None


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
        self._current_return_exact_type: str | None = None
        self._current_return_dict_info: DictTypeInfo | None = None
        self._current_return_set_info: SetTypeInfo | None = None
        self._current_return_tuple_info: TupleTypeInfo | None = None
        self._current_return_callable_info: CallableTypeInfo | None = None
        self._current_return_struct_qualified_name: str | None = None
        self._current_return_anonymous_struct_info: AnonymousStructTypeInfo | None = None
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
        self._struct_symbol_bindings: dict[str, str] = {}
        self._enum_analysis_cache: dict[str, EnumInstance] = {}
        self._enum_analysis_stack: list[str] = []
        self._lambda_counter = 0
        self._lexical_function_scopes: list[dict[str, LexicalFunctionInfo]] = []
        self.lexical_functions: dict[str, LexicalFunctionInfo] = {}
        self._loop_depth = 0

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

    def _resolve_enum_symbol(self, path: list[str]):
        """Resolve an enum path in the current module."""
        if self._current_module is None:
            return None
        return self.module_graph.resolve_enum_path(self._current_module, path)

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

    def _merge_exact_type_for_base(
        self,
        current_exact: str | None,
        incoming_exact: str | None,
        base_type: BaseType,
        label: str,
    ) -> str | None:
        """Merge exact-type spellings, requiring equality for nominal types."""
        current = normalize_exact_type(current_exact)
        incoming = normalize_exact_type(incoming_exact)
        if current is None:
            return incoming
        if incoming is None:
            return current
        if current == incoming:
            return current
        if base_type in {BaseType.INTEGER, BaseType.FLOAT}:
            return promote_exact_numeric(current, incoming, base_type)
        raise ZincTypeError(f"{label} use incompatible exact types")

    def _resolved_named_type_info(
        self,
        type_name: str | None,
        *,
        source_module_id: str | None,
        owner_qualified_name: str | None = None,
        owner_kind: str | None = None,
    ) -> ResolvedValueInfo:
        """Resolve a method-style return spelling into a rich value description."""
        if type_name is None:
            return ResolvedValueInfo(BaseType.VOID)
        if type_name == "Self":
            if owner_kind == "enum":
                return ResolvedValueInfo(BaseType.ENUM, exact_type=owner_qualified_name)
            return ResolvedValueInfo(
                BaseType.STRUCT,
                struct_qualified_name=owner_qualified_name,
            )

        exact_type = self._exact_type_name_from_text(type_name)
        base_type = exact_type_to_base(type_name)
        if base_type != BaseType.UNKNOWN:
            return ResolvedValueInfo(base_type, exact_type=exact_type)

        path = type_name.split(".")
        if source_module_id is not None:
            resolved_struct = self.module_graph.resolve_struct_path(source_module_id, path)
            if resolved_struct is not None:
                return ResolvedValueInfo(
                    BaseType.STRUCT,
                    struct_qualified_name=resolved_struct.qualified_name,
                )
            resolved_enum = self.module_graph.resolve_enum_path(source_module_id, path)
            if resolved_enum is not None:
                return ResolvedValueInfo(
                    BaseType.ENUM,
                    exact_type=resolved_enum.qualified_name,
                )
        return ResolvedValueInfo(BaseType.UNKNOWN)

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
        for enum in self.atlas.enums.values():
            self._analyze_enum(enum)

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
        while True:
            before = tuple(self.atlas.functions.keys())
            order = self.atlas.topological_order()  # callees first
            for mangled_name in order:
                func = self.atlas.functions[mangled_name]
                self._resolve_function(func)
            after = tuple(self.atlas.functions.keys())
            if after == before:
                break

        return self.symbols

    def _register_builtins(self) -> None:
        """Register built-in functions."""
        for name, base_type in (
            ("print", BaseType.VOID),
            ("chan", BaseType.CHANNEL),
            ("close", BaseType.VOID),
            ("dict", BaseType.DICT),
            ("sort_dict", BaseType.DICT),
            ("set", BaseType.SET),
            ("sort_set", BaseType.SET),
            ("meta", BaseType.STRUCT),
            ("type", BaseType.STRUCT),
            ("line", BaseType.INTEGER),
            ("has_component", BaseType.BOOLEAN),
            ("implements", BaseType.BOOLEAN),
        ):
            self.symbols.define(
                id=name,
                kind=SymbolKind.BUILTIN,
                resolved_type=base_type,
                interval=(-1, -1),
            )
        self.symbols.define(
            id="ComponentOrder",
            kind=SymbolKind.ENUM,
            resolved_type=BaseType.STRUCT,
            interval=(-1, -1),
            exact_type=COMPONENT_ORDER_QNAME,
        )

    def _analyze_struct(self, struct) -> None:
        """Analyze a struct declaration and populate fields/methods."""
        analyzed = self._analyze_struct_by_qualified_name(struct.qualified_name)
        struct.fields = [self._copy_struct_field(field) for field in analyzed.fields]
        struct.methods = [self._copy_struct_method(method) for method in analyzed.methods]
        struct.composition_mode = analyzed.composition_mode
        struct.composition_sources = analyzed.composition_sources

    def _analyze_enum(self, enum) -> None:
        """Analyze an enum declaration and populate variants/methods."""
        analyzed = self._analyze_enum_by_qualified_name(enum.qualified_name)
        enum.variants = [self._copy_enum_variant(variant) for variant in analyzed.variants]
        enum.methods = [self._copy_struct_method(method) for method in analyzed.methods]

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
            struct.infer_slot_names = tuple(
                field.name
                for field in fields
                if field.is_infer and field.source_struct_qualified_name == qualified_name
            )
            self._struct_analysis_cache[qualified_name] = struct
            return struct
        finally:
            self._struct_analysis_stack.pop()

    def _analyze_enum_by_qualified_name(self, qualified_name: str) -> EnumInstance:
        """Analyze an enum definition."""
        cached = self._enum_analysis_cache.get(qualified_name)
        if cached is not None:
            return cached

        if qualified_name in self._enum_analysis_stack:
            cycle = " -> ".join([*self._enum_analysis_stack, qualified_name])
            raise ZincTypeError(f"cyclic enum reference is not supported: {cycle}")

        symbol = self.module_graph.get_symbol(qualified_name)
        ctx: ZincParser.EnumDeclarationContext = symbol.ctx  # type: ignore[assignment]
        enum = EnumInstance(
            name=symbol.name,
            qualified_name=symbol.qualified_name,
            module_id=symbol.module_id,
            ctx=symbol.ctx,
        )

        self._enum_analysis_stack.append(qualified_name)
        try:
            variants: list[EnumVariantInfo] = []
            variant_names: set[str] = set()
            methods: list[StructMethodInfo] = []

            body = ctx.enumBody()
            if body is not None:
                for index, variant_ctx in enumerate(body.enumVariant()):
                    name = variant_ctx.IDENTIFIER().getText()
                    if name in variant_names:
                        raise ZincTypeError(f"enum '{symbol.name}' has duplicate variant '{name}'")
                    variant_names.add(name)
                    variants.append(
                        EnumVariantInfo(
                            name=name,
                            index=index,
                            fields=self._parse_enum_variant_fields(variant_ctx, qualified_name),
                            line_num=variant_ctx.start.line if variant_ctx.start is not None else 0,
                        )
                    )
                for method_ctx in body.functionDeclaration():
                    method = self._analyze_struct_method(
                        method_ctx,
                        {},
                        source_module_id=symbol.module_id,
                        constructor_owner_qualified_name=qualified_name,
                    )
                    if not method.is_static or self._method_body_uses_self(method.body_ctx):
                        raise ZincTypeError(f"enum method '{symbol.name}.{method.name}' cannot use self")
                    if method.name in variant_names:
                        raise ZincTypeError(
                            f"enum '{symbol.name}' has both a variant and method named '{method.name}'"
                        )
                    methods.append(method)

            enum.variants = variants
            enum.methods = methods
            self._enum_analysis_cache[qualified_name] = enum
            return enum
        finally:
            self._enum_analysis_stack.pop()

    def _copy_struct_field(self, field: StructFieldInfo) -> StructFieldInfo:
        """Clone field metadata when flattening composition."""
        return replace(
            field,
            array_info=self._copy_array_info(field.array_info),
            dict_info=self._copy_dict_info(field.dict_info),
            set_info=self._copy_set_info(field.set_info),
            tuple_info=self._copy_tuple_info(field.tuple_info),
            callable_info=self._copy_callable_info(field.callable_info),
            anonymous_struct_info=self._copy_anonymous_struct_info(field.anonymous_struct_info),
        )

    def _copy_enum_variant(self, variant: EnumVariantInfo) -> EnumVariantInfo:
        """Clone enum variant metadata."""
        return EnumVariantInfo(
            name=variant.name,
            index=variant.index,
            fields=[self._copy_struct_field(field) for field in variant.fields],
            line_num=variant.line_num,
        )

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
            array_info = None
            dict_info = None
            set_info = None
            tuple_info = None
            callable_info = None
            struct_qualified_name = None
            anonymous_struct_info = None
            is_infer = False

            # Field can have type annotation OR default value expression
            if field_ctx.type_():
                type_ann = field_ctx.type_().getText()
                is_infer = type_ann == "infer"
                if not is_infer:
                    (
                        resolved_type,
                        array_info,
                        dict_info,
                        set_info,
                        tuple_info,
                        callable_info,
                        struct_qualified_name,
                        anonymous_struct_info,
                    ) = self._type_metadata_from_type_ctx(field_ctx.type_())
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
                    exact_type=(
                        self._exact_type_name_from_type_ctx(field_ctx.type_())
                        if field_ctx.type_() and not is_infer
                        else None
                    ),
                    array_info=self._copy_array_info(array_info) if field_ctx.type_() else None,
                    dict_info=self._copy_dict_info(dict_info) if field_ctx.type_() else None,
                    set_info=self._copy_set_info(set_info) if field_ctx.type_() else None,
                    tuple_info=self._copy_tuple_info(tuple_info) if field_ctx.type_() else None,
                    callable_info=callable_info if field_ctx.type_() else None,
                    struct_qualified_name=struct_qualified_name if field_ctx.type_() else None,
                    anonymous_struct_info=anonymous_struct_info if field_ctx.type_() else None,
                    source_struct_qualified_name=source_struct_qualified_name,
                    is_infer=is_infer,
                    line_num=field_ctx.start.line if field_ctx.start is not None else 0,
                )
            )

        return fields

    def _parse_enum_variant_fields(
        self,
        ctx: ZincParser.EnumVariantContext,
        source_enum_qualified_name: str,
    ) -> list[StructFieldInfo]:
        """Parse named payload fields for one enum variant."""
        fields: list[StructFieldInfo] = []
        seen: set[str] = set()
        for field_ctx in ctx.enumVariantFieldType():
            name = field_ctx.IDENTIFIER().getText()
            if name in seen:
                raise ZincTypeError(
                    f"enum variant '{ctx.IDENTIFIER().getText()}' has duplicate field '{name}'"
                )
            seen.add(name)
            (
                resolved_type,
                array_info,
                dict_info,
                set_info,
                tuple_info,
                callable_info,
                struct_qualified_name,
                anonymous_struct_info,
            ) = self._type_metadata_from_type_ctx(field_ctx.type_())
            fields.append(
                StructFieldInfo(
                    name=name,
                    type_annotation=field_ctx.type_().getText(),
                    resolved_type=resolved_type,
                    exact_type=self._exact_type_name_from_type_ctx(field_ctx.type_()),
                    array_info=self._copy_array_info(array_info),
                    dict_info=self._copy_dict_info(dict_info),
                    set_info=self._copy_set_info(set_info),
                    tuple_info=self._copy_tuple_info(tuple_info),
                    callable_info=self._copy_callable_info(callable_info),
                    struct_qualified_name=struct_qualified_name,
                    anonymous_struct_info=self._copy_anonymous_struct_info(anonymous_struct_info),
                    source_struct_qualified_name=source_enum_qualified_name,
                    line_num=field_ctx.start.line if field_ctx.start is not None else 0,
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
            line_num=ctx.start.line if ctx.start is not None else 0,
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
                if primary and hasattr(primary, "enumVariantConstruction") and primary.enumVariantConstruction():
                    inst = primary.enumVariantConstruction()
                    variant_target = self.module_graph.resolve_enum_variant_path(
                        source_module_id,
                        enum_variant_path_from_ctx(inst),
                    )
                    if variant_target is not None:
                        enum_symbol, _variant_name = variant_target
                        if enum_symbol.qualified_name == constructor_owner_qualified_name:
                            return "Self"
                        return enum_symbol.name
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
                path = extract_identifier_path(expr_ctx)
                if path:
                    variant_target = self.module_graph.resolve_enum_variant_path(source_module_id, path)
                    if variant_target is not None:
                        enum_symbol, _variant_name = variant_target
                        if enum_symbol.qualified_name == constructor_owner_qualified_name:
                            return "Self"
                        return enum_symbol.name
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

    def _method_body_uses_self(self, node) -> bool:
        """Return True when a method body references the special self binding."""
        if node is None:
            return False
        if isinstance(node, ZincParser.PrimaryExpressionContext) and node.getText() == "self":
            return True
        if hasattr(node, "getChildCount"):
            for i in range(node.getChildCount()):
                child = node.getChild(i)
                if isinstance(child, ParserRuleContext) and self._method_body_uses_self(child):
                    return True
        return False

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
        if type_name == "Self":
            return BaseType.STRUCT
        return exact_type_to_base(type_name)

    def _exact_type_name_from_text(self, type_name: str | None) -> str | None:
        """Return the canonical exact scalar type for a primitive annotation."""
        if type_name == "Self":
            return None
        normalized = normalize_exact_type(type_name)
        if normalized is None:
            return None
        return normalized if exact_type_to_base(normalized) != BaseType.UNKNOWN else None

    def _exact_type_name_from_type_ctx(self, type_ctx) -> str | None:
        """Return the exact scalar type encoded by a type annotation, if any."""
        if type_ctx is None:
            return None
        exact_type = self._exact_type_name_from_text(type_ctx.getText())
        if exact_type is not None:
            return exact_type
        if hasattr(type_ctx, "qualifiedName") and type_ctx.qualifiedName() and not type_ctx.typeList():
            resolved_enum = self._resolve_enum_symbol(type_ctx.qualifiedName().getText().split("."))
            if resolved_enum is not None:
                return resolved_enum.qualified_name
        return None

    def _resolved_exact_type(self, base_type: BaseType, exact_type: str | None) -> str | None:
        """Return the concrete scalar type spelling to use for a primitive value."""
        if exact_type is not None:
            return normalize_exact_type(exact_type)
        return default_exact_type(base_type)

    def _parse_constant_literal(self, text: str) -> object | None:
        """Parse a literal token into a Python value for fit checks."""
        base_type = parse_literal(text)
        if base_type == BaseType.INTEGER:
            return int(text, 0)
        if base_type == BaseType.FLOAT:
            return float(text)
        if base_type == BaseType.BOOLEAN:
            return text == "true"
        if base_type == BaseType.STRING:
            return text[1:-1]
        return None

    def _is_compile_time_literal_expr(self, expr_ctx) -> bool:
        """Return True when an expression is composed only of literal operators."""
        if expr_ctx is None:
            return False
        if isinstance(expr_ctx, ZincParser.PrimaryExprContext):
            primary = expr_ctx.primaryExpression()
            return bool(primary and primary.literal())
        if isinstance(expr_ctx, ZincParser.ParenExprContext):
            return self._is_compile_time_literal_expr(expr_ctx.expression())
        if isinstance(expr_ctx, ZincParser.UnaryExprContext):
            return self._is_compile_time_literal_expr(expr_ctx.expression())
        if isinstance(expr_ctx, (ZincParser.AdditiveExprContext, ZincParser.MultiplicativeExprContext)):
            return all(self._is_compile_time_literal_expr(expr_ctx.expression(i)) for i in range(2))
        return False

    def _literal_constant_value_for_expr(self, expr_ctx, expr_symbol: Symbol | None) -> object | None:
        """Return a fit-check constant only for literal expressions, not typed bindings."""
        if expr_symbol is None or not self._is_compile_time_literal_expr(expr_ctx):
            return None
        return expr_symbol.constant_value

    def _type_metadata_from_type_ctx(
        self,
        type_ctx,
    ) -> tuple[
        BaseType,
        ArrayTypeInfo | None,
        DictTypeInfo | None,
        SetTypeInfo | None,
        TupleTypeInfo | None,
        CallableTypeInfo | None,
        str | None,
        AnonymousStructTypeInfo | None,
    ]:
        """Resolve a parsed type annotation into Zinc base and rich metadata."""
        if type_ctx is None:
            return BaseType.UNKNOWN, None, None, None, None, None, None, None

        if hasattr(type_ctx, "anonymousStructType") and type_ctx.anonymousStructType():
            anon_ctx = type_ctx.anonymousStructType()
            seen: set[str] = set()
            fields: list[AnonymousStructFieldInfo] = []
            for field_ctx in anon_ctx.anonymousStructFieldType():
                field_name = field_ctx.IDENTIFIER().getText()
                if field_name in seen:
                    raise ZincTypeError(f"anonymous struct type has duplicate field '{field_name}'")
                seen.add(field_name)
                (
                    field_type,
                    field_array,
                    field_dict,
                    field_set,
                    field_tuple,
                    field_callable,
                    field_struct_qualified_name,
                    field_anonymous_struct_info,
                ) = self._type_metadata_from_type_ctx(field_ctx.type_())
                fields.append(
                    AnonymousStructFieldInfo(
                        name=field_name,
                        resolved_type=field_type,
                        exact_type=self._exact_type_name_from_type_ctx(field_ctx.type_()),
                        array_info=self._copy_array_info(field_array),
                        dict_info=self._copy_dict_info(field_dict),
                        set_info=self._copy_set_info(field_set),
                        tuple_info=self._copy_tuple_info(field_tuple),
                        callable_info=self._copy_callable_info(field_callable),
                        struct_qualified_name=field_struct_qualified_name,
                        anonymous_struct_info=self._copy_anonymous_struct_info(field_anonymous_struct_info),
                    )
                )
            return BaseType.STRUCT, None, None, None, None, None, None, AnonymousStructTypeInfo(fields=fields)

        if type_ctx.tupleType():
            tuple_ctx = type_ctx.tupleType()
            element_types: list[BaseType] = []
            element_exact_types: list[str | None] = []
            element_tuple_infos: dict[int, TupleTypeInfo] = {}
            element_callable_infos: dict[int, CallableTypeInfo] = {}
            element_struct_qualified_names: dict[int, str] = {}
            element_anonymous_struct_infos: dict[int, AnonymousStructTypeInfo] = {}
            for i, element_ctx in enumerate(tuple_ctx.type_()):
                (
                    element_type,
                    _element_array,
                    _element_dict,
                    _element_set,
                    element_tuple,
                    element_callable,
                    element_struct_qualified_name,
                    element_anonymous_struct_info,
                ) = self._type_metadata_from_type_ctx(element_ctx)
                element_types.append(element_type)
                element_exact_types.append(self._exact_type_name_from_type_ctx(element_ctx))
                if element_tuple is not None:
                    element_tuple_infos[i] = element_tuple
                if element_callable is not None:
                    element_callable_infos[i] = element_callable
                if element_struct_qualified_name is not None:
                    element_struct_qualified_names[i] = element_struct_qualified_name
                if element_anonymous_struct_info is not None:
                    element_anonymous_struct_infos[i] = element_anonymous_struct_info
            return (
                BaseType.TUPLE,
                None,
                None,
                None,
                TupleTypeInfo(
                    element_types=element_types,
                    element_exact_types=element_exact_types,
                    element_tuple_infos=element_tuple_infos,
                    element_callable_infos=element_callable_infos,
                    element_struct_qualified_names=element_struct_qualified_names,
                    element_anonymous_struct_infos=element_anonymous_struct_infos,
                ),
                None,
                None,
                None,
            )

        if type_ctx.LBRACK():
            (
                element_type,
                _nested_array,
                _nested_dict,
                _nested_set,
                element_tuple,
                element_callable,
                element_struct_qualified_name,
                element_anonymous_struct_info,
            ) = self._type_metadata_from_type_ctx(type_ctx.type_())
            return (
                BaseType.ARRAY,
                ArrayTypeInfo(
                    element_type=element_type,
                    element_exact_type=self._exact_type_name_from_type_ctx(type_ctx.type_()),
                    element_tuple_info=element_tuple,
                    element_callable_info=element_callable,
                    element_struct_qualified_name=element_struct_qualified_name,
                    element_anonymous_struct_info=element_anonymous_struct_info,
                ),
                None,
                None,
                None,
                None,
                None,
                None,
            )

        if type_ctx.RARROW():
            param_types: list[BaseType] = []
            param_exact_types: list[str | None] = []
            param_array_infos: dict[int, ArrayTypeInfo] = {}
            param_dict_infos: dict[int, DictTypeInfo] = {}
            param_set_infos: dict[int, SetTypeInfo] = {}
            param_tuple_infos: dict[int, TupleTypeInfo] = {}
            param_callable_infos: dict[int, CallableTypeInfo] = {}
            param_struct_qualified_names: dict[int, str] = {}
            param_anonymous_struct_infos: dict[int, AnonymousStructTypeInfo] = {}
            param_ctxs = list(type_ctx.typeList().type_()) if type_ctx.typeList() else []
            for i, param_ctx in enumerate(param_ctxs):
                (
                    param_type,
                    param_array,
                    param_dict,
                    param_set,
                    param_tuple,
                    param_callable,
                    param_struct_qualified_name,
                    param_anonymous_struct_info,
                ) = self._type_metadata_from_type_ctx(param_ctx)
                param_types.append(param_type)
                param_exact_types.append(self._exact_type_name_from_type_ctx(param_ctx))
                if param_array is not None:
                    param_array_infos[i] = param_array
                if param_dict is not None:
                    param_dict_infos[i] = param_dict
                if param_set is not None:
                    param_set_infos[i] = param_set
                if param_tuple is not None:
                    param_tuple_infos[i] = param_tuple
                if param_callable is not None:
                    param_callable_infos[i] = param_callable
                if param_struct_qualified_name is not None:
                    param_struct_qualified_names[i] = param_struct_qualified_name
                if param_anonymous_struct_info is not None:
                    param_anonymous_struct_infos[i] = param_anonymous_struct_info

            (
                return_type,
                _return_array,
                return_dict,
                return_set,
                return_tuple,
                return_callable,
                return_struct_qualified_name,
                return_anonymous_struct_info,
            ) = self._type_metadata_from_type_ctx(type_ctx.type_())
            return (
                BaseType.CALLABLE,
                None,
                None,
                None,
                None,
                CallableTypeInfo(
                    param_types=param_types,
                    param_exact_types=param_exact_types,
                    param_array_infos=param_array_infos,
                    param_dict_infos=param_dict_infos,
                    param_set_infos=param_set_infos,
                    param_tuple_infos=param_tuple_infos,
                    param_callable_infos=param_callable_infos,
                    param_struct_qualified_names=param_struct_qualified_names,
                    param_anonymous_struct_infos=param_anonymous_struct_infos,
                    return_type=return_type,
                    return_exact_type=self._exact_type_name_from_type_ctx(type_ctx.type_()),
                    return_dict_info=return_dict,
                    return_set_info=return_set,
                    return_tuple_info=return_tuple,
                    return_callable_info=return_callable,
                    return_struct_qualified_name=return_struct_qualified_name,
                    return_anonymous_struct_info=return_anonymous_struct_info,
                ),
                None,
                None,
            )

        if type_ctx.qualifiedName():
            type_name = type_ctx.qualifiedName().getText()
            base_type = self._type_name_to_base(type_name)
            type_list = type_ctx.typeList()
            if type_list and base_type == BaseType.UNKNOWN:
                generic_name = type_name.lower()
                args = list(type_list.type_())
                if generic_name in {"dict", "sort_dict"} and len(args) == 2:
                    (
                        key_type,
                        _key_array,
                        _key_dict,
                        _key_set,
                        _key_tuple,
                        key_callable,
                        key_struct_qualified_name,
                        key_anonymous_struct_info,
                    ) = self._type_metadata_from_type_ctx(args[0])
                    (
                        value_type,
                        _value_array,
                        _value_dict,
                        _value_set,
                        _value_tuple,
                        value_callable,
                        value_struct_qualified_name,
                        value_anonymous_struct_info,
                    ) = self._type_metadata_from_type_ctx(args[1])
                    return (
                        BaseType.DICT,
                        None,
                        DictTypeInfo(
                            key_type=key_type,
                            value_type=value_type,
                            key_exact_type=self._exact_type_name_from_type_ctx(args[0]),
                            value_exact_type=self._exact_type_name_from_type_ctx(args[1]),
                            key_callable_info=key_callable,
                            value_callable_info=value_callable,
                            key_struct_qualified_name=key_struct_qualified_name,
                            value_struct_qualified_name=value_struct_qualified_name,
                            key_anonymous_struct_info=key_anonymous_struct_info,
                            value_anonymous_struct_info=value_anonymous_struct_info,
                            kind=generic_name,
                        ),
                        None,
                        None,
                        None,
                        None,
                        None,
                    )
                if generic_name in {"set", "sort_set"} and len(args) == 1:
                    (
                        element_type,
                        _element_array,
                        _element_dict,
                        _element_set,
                        _element_tuple,
                        _element_callable,
                        element_struct_qualified_name,
                        element_anonymous_struct_info,
                    ) = self._type_metadata_from_type_ctx(args[0])
                    return (
                        BaseType.SET,
                        None,
                        None,
                        SetTypeInfo(
                            element_type=element_type,
                            element_exact_type=self._exact_type_name_from_type_ctx(args[0]),
                            element_struct_qualified_name=element_struct_qualified_name,
                            element_anonymous_struct_info=element_anonymous_struct_info,
                            kind=generic_name,
                        ),
                        None,
                        None,
                        None,
                        None,
                    )
            if base_type == BaseType.UNKNOWN:
                resolved_struct = self._resolve_struct_symbol(type_name.split("."))
                if resolved_struct is not None:
                    return BaseType.STRUCT, None, None, None, None, None, resolved_struct.qualified_name, None
                resolved_enum = self._resolve_enum_symbol(type_name.split("."))
                if resolved_enum is not None:
                    return BaseType.ENUM, None, None, None, None, None, None, None
            return base_type, None, None, None, None, None, None, None

        return BaseType.UNKNOWN, None, None, None, None, None, None, None

    def _assignment_types_compatible(self, expected: BaseType, actual: BaseType) -> bool:
        """Return True when an assignment is compatible under Zinc's simple rules."""
        if actual == BaseType.NEVER:
            return True
        if expected == BaseType.NEVER:
            return actual == BaseType.NEVER
        if expected == BaseType.UNKNOWN or actual == BaseType.UNKNOWN:
            return True
        if expected == actual:
            return True
        return expected in {BaseType.INTEGER, BaseType.FLOAT} and actual in {BaseType.INTEGER, BaseType.FLOAT}

    def _integer_value_fits_exact_type(self, value: int, exact_type: str) -> bool:
        """Return True when an integer literal fits a target integer type."""
        ranges = {
            "i8": (-(2 ** 7), 2 ** 7 - 1),
            "i16": (-(2 ** 15), 2 ** 15 - 1),
            "i32": (-(2 ** 31), 2 ** 31 - 1),
            "i64": (-(2 ** 63), 2 ** 63 - 1),
            "i128": (-(2 ** 127), 2 ** 127 - 1),
            "u8": (0, 2 ** 8 - 1),
            "u16": (0, 2 ** 16 - 1),
            "u32": (0, 2 ** 32 - 1),
            "u64": (0, 2 ** 64 - 1),
            "u128": (0, 2 ** 128 - 1),
        }
        bounds = ranges.get(exact_type)
        if bounds is None:
            return False
        lower, upper = bounds
        return lower <= value <= upper

    def _exact_types_compatible(
        self,
        expected_type: BaseType,
        actual_type: BaseType,
        *,
        expected_exact_type: str | None = None,
        actual_exact_type: str | None = None,
        actual_constant_value: object | None = None,
    ) -> bool:
        """Return True when exact scalar typing rules are satisfied."""
        if actual_type == BaseType.NEVER:
            return True
        if not self._assignment_types_compatible(expected_type, actual_type):
            return False

        expected_exact = normalize_exact_type(expected_exact_type)
        if expected_exact is None:
            return True

        actual_exact = normalize_exact_type(actual_exact_type)
        if actual_constant_value is not None:
            if expected_type == BaseType.INTEGER and isinstance(actual_constant_value, int):
                return self._integer_value_fits_exact_type(actual_constant_value, expected_exact)
            if expected_type == BaseType.FLOAT and isinstance(actual_constant_value, float):
                return expected_exact.startswith("f")
            if expected_type == BaseType.BOOLEAN and isinstance(actual_constant_value, bool):
                return expected_exact == "bool"
            if expected_type == BaseType.STRING and isinstance(actual_constant_value, str):
                return expected_exact == "String"

        if actual_exact is None:
            return False
        return expected_exact == actual_exact

    def _assignment_metadata_compatible(
        self,
        expected_type: BaseType,
        actual_type: BaseType,
        *,
        expected_exact_type: str | None = None,
        actual_exact_type: str | None = None,
        actual_constant_value: object | None = None,
        expected_array: ArrayTypeInfo | None = None,
        actual_array: ArrayTypeInfo | None = None,
        expected_dict: DictTypeInfo | None = None,
        actual_dict: DictTypeInfo | None = None,
        expected_set: SetTypeInfo | None = None,
        actual_set: SetTypeInfo | None = None,
        expected_tuple: TupleTypeInfo | None = None,
        actual_tuple: TupleTypeInfo | None = None,
        expected_callable: CallableTypeInfo | None = None,
        actual_callable: CallableTypeInfo | None = None,
        expected_struct_qualified_name: str | None = None,
        actual_struct_qualified_name: str | None = None,
        expected_anonymous_struct_info: AnonymousStructTypeInfo | None = None,
        actual_anonymous_struct_info: AnonymousStructTypeInfo | None = None,
    ) -> bool:
        """Return True when assignment-compatible rich type metadata matches."""
        if not self._exact_types_compatible(
            expected_type,
            actual_type,
            expected_exact_type=expected_exact_type,
            actual_exact_type=actual_exact_type,
            actual_constant_value=actual_constant_value,
        ):
            return False
        if expected_type == BaseType.STRUCT:
            return self._structs_compatible(
                expected_struct_qualified_name,
                expected_anonymous_struct_info,
                actual_struct_qualified_name,
                actual_anonymous_struct_info,
            )
        if expected_type == BaseType.ARRAY:
            return self._array_elements_compatible(expected_array, actual_array)
        if expected_type == BaseType.TUPLE:
            return self._tuple_infos_compatible(expected_tuple, actual_tuple)
        if expected_type == BaseType.CALLABLE:
            if expected_callable is None or actual_callable is None:
                return expected_callable is None and actual_callable is None
            try:
                self._merge_callable_info(expected_callable, actual_callable, "callable assignment")
            except ZincTypeError:
                return False
            return True
        if expected_type == BaseType.SET:
            if expected_set is None or actual_set is None:
                return expected_set is None and actual_set is None
            if not self._exact_types_compatible(
                expected_set.element_type,
                actual_set.element_type,
                expected_exact_type=expected_set.element_exact_type,
                actual_exact_type=actual_set.element_exact_type,
            ):
                return False
            if expected_set.element_type == BaseType.STRUCT:
                return self._structs_compatible(
                    expected_set.element_struct_qualified_name,
                    expected_set.element_anonymous_struct_info,
                    actual_set.element_struct_qualified_name,
                    actual_set.element_anonymous_struct_info,
                )
        if expected_type == BaseType.DICT:
            if expected_dict is None or actual_dict is None:
                return expected_dict is None and actual_dict is None
            if not self._exact_types_compatible(
                expected_dict.key_type,
                actual_dict.key_type,
                expected_exact_type=expected_dict.key_exact_type,
                actual_exact_type=actual_dict.key_exact_type,
            ):
                return False
            if not self._exact_types_compatible(
                expected_dict.value_type,
                actual_dict.value_type,
                expected_exact_type=expected_dict.value_exact_type,
                actual_exact_type=actual_dict.value_exact_type,
            ):
                return False
            if expected_dict.key_type == BaseType.STRUCT and not self._structs_compatible(
                expected_dict.key_struct_qualified_name,
                expected_dict.key_anonymous_struct_info,
                actual_dict.key_struct_qualified_name,
                actual_dict.key_anonymous_struct_info,
            ):
                return False
            if expected_dict.value_type == BaseType.STRUCT and not self._structs_compatible(
                expected_dict.value_struct_qualified_name,
                expected_dict.value_anonymous_struct_info,
                actual_dict.value_struct_qualified_name,
                actual_dict.value_anonymous_struct_info,
            ):
                return False
        return True

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
        return info.copy() if info is not None else None

    def _copy_set_info(self, info: SetTypeInfo | None) -> SetTypeInfo | None:
        """Copy set metadata so symbols do not accidentally share construction state."""
        return info.copy() if info is not None else None

    def _copy_array_info(self, info: ArrayTypeInfo | None) -> ArrayTypeInfo | None:
        """Copy array metadata, including tuple element metadata."""
        return info.copy() if info is not None else None

    def _copy_channel_info(self, info: ChannelTypeInfo | None) -> ChannelTypeInfo | None:
        """Copy channel metadata so callable element refinements can be merged safely."""
        return info.copy() if info is not None else None

    def _copy_tuple_info(self, info: TupleTypeInfo | None) -> TupleTypeInfo | None:
        """Copy tuple metadata recursively."""
        return info.copy() if info is not None else None

    def _copy_callable_info(self, info: CallableTypeInfo | None) -> CallableTypeInfo | None:
        """Copy callable metadata recursively."""
        return info.copy() if info is not None else None

    def _copy_anonymous_struct_info(
        self,
        info: AnonymousStructTypeInfo | None,
    ) -> AnonymousStructTypeInfo | None:
        """Copy anonymous struct metadata recursively."""
        return info.copy() if info is not None else None

    def _value_info_from_symbol(
        self,
        base_type: BaseType,
        symbol: Symbol | None,
    ) -> ResolvedValueInfo:
        """Build a rich value description from a resolved type and optional symbol."""
        struct_qualified_name = None
        anonymous_struct_info = None
        if base_type == BaseType.STRUCT and symbol is not None:
            struct_qualified_name, anonymous_struct_info = self._struct_metadata_for_symbol(symbol)

        return ResolvedValueInfo(
            base_type=base_type,
            exact_type=symbol.exact_type if symbol else self._resolved_exact_type(base_type, None),
            array_info=self._array_info_from_symbol(symbol) if base_type == BaseType.ARRAY else None,
            channel_info=self._copy_channel_info(symbol.channel_info) if base_type == BaseType.CHANNEL and symbol else None,
            dict_info=self._copy_dict_info(symbol.dict_info) if base_type == BaseType.DICT and symbol else None,
            set_info=self._copy_set_info(symbol.set_info) if base_type == BaseType.SET and symbol else None,
            tuple_info=self._copy_tuple_info(symbol.tuple_info) if base_type == BaseType.TUPLE and symbol else None,
            callable_info=self._copy_callable_info(symbol.callable_info) if base_type == BaseType.CALLABLE and symbol else None,
            struct_qualified_name=struct_qualified_name,
            anonymous_struct_info=self._copy_anonymous_struct_info(anonymous_struct_info),
        )

    def _value_info_from_expression(self, expr_ctx) -> ResolvedValueInfo:
        """Visit an expression and return its full value metadata."""
        expr_type = self.visit(expr_ctx)
        return self._value_info_from_symbol(expr_type, self._expr_symbol(expr_ctx))

    def _record_value_info(self, interval: tuple[int, int], info: ResolvedValueInfo) -> Symbol:
        """Materialize a temporary symbol from rich value metadata."""
        temp = self.symbols.define_temp(
            resolved_type=info.base_type,
            interval=interval,
            exact_type=info.exact_type,
            constant_value=None,
        )
        if info.base_type == BaseType.ARRAY and info.array_info is not None:
            temp.element_type = info.array_info.element_type
            temp.element_exact_type = info.array_info.element_exact_type
            temp.tuple_info = self._copy_tuple_info(info.array_info.element_tuple_info)
            temp.callable_info = self._copy_callable_info(info.array_info.element_callable_info)
            temp.element_struct_qualified_name = info.array_info.element_struct_qualified_name
            temp.element_anonymous_struct_info = self._copy_anonymous_struct_info(
                info.array_info.element_anonymous_struct_info
            )
        elif info.base_type == BaseType.CHANNEL and info.channel_info is not None:
            temp.channel_info = self._copy_channel_info(info.channel_info)
        elif info.base_type == BaseType.DICT and info.dict_info is not None:
            temp.dict_info = self._copy_dict_info(info.dict_info)
        elif info.base_type == BaseType.SET and info.set_info is not None:
            temp.set_info = self._copy_set_info(info.set_info)
        elif info.base_type == BaseType.TUPLE and info.tuple_info is not None:
            temp.tuple_info = self._copy_tuple_info(info.tuple_info)
        elif info.base_type == BaseType.CALLABLE and info.callable_info is not None:
            temp.callable_info = self._copy_callable_info(info.callable_info)
        elif info.base_type == BaseType.STRUCT:
            temp.anonymous_struct_info = self._copy_anonymous_struct_info(info.anonymous_struct_info)
            if info.struct_qualified_name is not None:
                self._struct_symbol_bindings[temp.unique_name] = info.struct_qualified_name
        return temp

    def _module_source_file(self, module_id: str | None) -> str:
        """Return the source path for a module id."""
        if module_id is None:
            return ""
        return self.module_graph.get_module(module_id).path.as_posix()

    def _public_fqn(self, qualified_name: str | None) -> str:
        """Render a public slash-separated FQN."""
        if not qualified_name:
            return ""
        return qualified_name.replace("::", "/")

    def _qualified_name_tail(self, qualified_name: str | None) -> str:
        """Return the unqualified tail name for a canonical symbol id."""
        if not qualified_name:
            return ""
        return qualified_name.rpartition("::")[2] or qualified_name

    def _current_owner_name(self) -> str:
        """Return the current function-ish owner display name."""
        if self._current_function and self._current_function in self.atlas.functions:
            return self.atlas.functions[self._current_function].name
        if self._current_function and self._current_function in self.lexical_functions:
            return self.lexical_functions[self._current_function].display_name
        return self._current_function or "global"

    def _current_owner_fqn(self) -> str:
        """Return the current function-ish owner FQN."""
        if self._current_function and self._current_function in self.atlas.functions:
            return self._public_fqn(self.atlas.functions[self._current_function].qualified_name)
        if self._current_module is None:
            return self._current_owner_name()
        return f"{self._current_module}/{self._current_owner_name()}"

    def _base_meta_fields(
        self,
        *,
        kind: str,
        name: str,
        fqn: str,
        module_fqn: str,
        file: str,
        line_num: int,
        is_public: bool,
    ) -> dict[str, object]:
        """Build the common field set shared by BaseMeta shapes."""
        return {
            "kind": kind,
            "name": name,
            "fqn": fqn,
            "module_fqn": module_fqn,
            "file": file,
            "line_num": line_num,
            "is_public": is_public,
        }

    def _scalar_constant_type_meta(self, value: object) -> MetaValue:
        """Return TypeMeta for a literal scalar constant."""
        if isinstance(value, bool):
            return self._type_meta_from_base(
                BaseType.BOOLEAN,
                exact_type="bool",
            )
        if isinstance(value, int):
            return self._type_meta_from_base(
                BaseType.INTEGER,
                exact_type="i64",
            )
        if isinstance(value, float):
            return self._type_meta_from_base(
                BaseType.FLOAT,
                exact_type="f64",
            )
        if isinstance(value, str):
            return self._type_meta_from_base(
                BaseType.STRING,
                exact_type="String",
            )
        return unknown_type_meta(type(value).__name__)

    def _type_meta_list(self, items: list[MetaValue]) -> MetaListValue:
        """Return a typed metadata list of TypeMeta values."""
        return MetaListValue(
            items=list(items),
            element_base_type=BaseType.STRUCT,
            element_struct_qualified_name=TYPE_META_QNAME,
        )

    def _string_meta_list(self, items: list[str]) -> MetaListValue:
        """Return a typed metadata list of strings."""
        return MetaListValue(
            items=list(items),
            element_base_type=BaseType.STRING,
            element_exact_type="String",
        )

    def _metadata_list(self, items: list[MetaValue], item_qname: str) -> MetaListValue:
        """Return a typed metadata list for one metadata object shape."""
        return MetaListValue(
            items=list(items),
            element_base_type=BaseType.STRUCT,
            element_struct_qualified_name=item_qname,
        )

    def _record_constant_value(
        self,
        interval: tuple[int, int],
        value: object,
        *,
        line_num: int = 0,
    ) -> Symbol:
        """Materialize a temp symbol from a compile-time constant value."""
        if isinstance(value, MetaValue):
            temp = self.symbols.define_temp(
                resolved_type=BaseType.STRUCT,
                interval=interval,
                constant_value=value,
                line_num=line_num,
            )
            self._struct_symbol_bindings[temp.unique_name] = value.struct_qualified_name
            return temp
        if isinstance(value, MetaListValue):
            temp = self.symbols.define_temp(
                resolved_type=BaseType.ARRAY,
                interval=interval,
                constant_value=value,
                line_num=line_num,
            )
            temp.element_type = value.element_base_type
            temp.element_exact_type = value.element_exact_type
            temp.element_struct_qualified_name = value.element_struct_qualified_name
            temp.element_anonymous_struct_info = self._copy_anonymous_struct_info(
                value.element_anonymous_struct_info
            )
            return temp
        if isinstance(value, bool):
            return self.symbols.define_temp(
                resolved_type=BaseType.BOOLEAN,
                interval=interval,
                exact_type="bool",
                constant_value=value,
                line_num=line_num,
            )
        if isinstance(value, int):
            return self.symbols.define_temp(
                resolved_type=BaseType.INTEGER,
                interval=interval,
                exact_type="i64",
                constant_value=value,
                line_num=line_num,
            )
        if isinstance(value, float):
            return self.symbols.define_temp(
                resolved_type=BaseType.FLOAT,
                interval=interval,
                exact_type="f64",
                constant_value=value,
                line_num=line_num,
            )
        if isinstance(value, str):
            return self.symbols.define_temp(
                resolved_type=BaseType.STRING,
                interval=interval,
                exact_type="String",
                constant_value=value,
                line_num=line_num,
            )
        return self.symbols.define_temp(
            resolved_type=BaseType.UNKNOWN,
            interval=interval,
            constant_value=value,
            line_num=line_num,
        )

    def _struct_type_kind_name(self, exact_type: str | None) -> str:
        """Return a TypeMeta kind label for a scalar-like exact type."""
        if exact_type == "__ZincContext":
            return "context"
        return "primitive"

    def _type_meta_from_base(
        self,
        base_type: BaseType,
        *,
        exact_type: str | None = None,
        array_info: ArrayTypeInfo | None = None,
        dict_info: DictTypeInfo | None = None,
        set_info: SetTypeInfo | None = None,
        tuple_info: TupleTypeInfo | None = None,
        callable_info: CallableTypeInfo | None = None,
        struct_qualified_name: str | None = None,
        anonymous_struct_info: AnonymousStructTypeInfo | None = None,
    ) -> MetaValue:
        """Build TypeMeta for a concrete Zinc type."""
        def has_symbol(qualified_name: str | None, *, kinds: tuple[str, ...]) -> bool:
            if not qualified_name:
                return False
            try:
                symbol = self.module_graph.get_symbol(qualified_name)
            except KeyError:
                return False
            return symbol.kind in kinds

        if base_type == BaseType.STRUCT:
            struct_name = self._qualified_name_tail(struct_qualified_name)
            family_name = struct_name or "AnonymousStruct"
            family_fqn = self._public_fqn(struct_qualified_name) or family_name
            args: list[MetaValue] = []
            infer_slots: list[str] = []
            field_metas: list[MetaValue] = []
            method_metas: list[MetaValue] = []
            component_metas: list[MetaValue] = []
            recursive_component_metas: list[MetaValue] = []
            struct_info: StructInstance | None = None
            if has_symbol(struct_qualified_name, kinds=("struct",)):
                struct_info = self._analyze_struct_by_qualified_name(struct_qualified_name)
                infer_slots = list(struct_info.infer_slot_names)
                if anonymous_struct_info is not None:
                    for slot_name in infer_slots:
                        slot_field = anonymous_struct_info.get_field(slot_name)
                        if slot_field is not None:
                            args.append(
                                self._type_meta_from_base(
                                    slot_field.resolved_type,
                                    exact_type=slot_field.exact_type,
                                    array_info=slot_field.array_info,
                                    dict_info=slot_field.dict_info,
                                    set_info=slot_field.set_info,
                                    tuple_info=slot_field.tuple_info,
                                    callable_info=slot_field.callable_info,
                                    struct_qualified_name=slot_field.struct_qualified_name,
                                    anonymous_struct_info=slot_field.anonymous_struct_info,
                                )
                            )
                field_metas = [
                    self._field_meta_from_info(
                        struct_info,
                        field,
                        index,
                    )
                    for index, field in enumerate(struct_info.fields)
                    if not field.is_private
                ]
                method_metas = [
                    self._method_meta_from_info(struct_info, method)
                    for method in struct_info.methods
                    if not method.name.startswith("_")
                ]
                component_metas = [
                    self._type_meta_from_base(BaseType.STRUCT, struct_qualified_name=component_name)
                    for component_name in struct_info.composition_sources
                ]
                recursive_component_metas = self._recursive_component_type_metas(
                    struct_info.composition_sources,
                    order="depth_first",
                )
            display_name = family_name
            display_fqn = family_fqn
            if args:
                rendered_args = ", ".join(str(arg.fields["name"]) for arg in args)
                display_name = f"{family_name}<{rendered_args}>"
                display_fqn = f"{family_fqn}<{rendered_args}>"
            type_meta = MetaValue(
                struct_qualified_name=TYPE_META_QNAME,
                fields={
                    "kind": "struct",
                    "name": display_name,
                    "fqn": display_fqn,
                    "family_name": family_name,
                    "family_fqn": family_fqn,
                    "args": self._type_meta_list(args),
                    "is_named": bool(struct_qualified_name),
                    "infer_slots": self._string_meta_list(infer_slots),
                },
            )
            type_meta.methods = {
                "fields": self._metadata_list(field_metas, FIELD_META_QNAME),
                "methods": self._metadata_list(method_metas, METHOD_META_QNAME),
                "components": self._type_meta_list(component_metas),
                "recursive_components": lambda args: self._type_meta_list(
                    self._recursive_component_type_metas(
                        struct_info.composition_sources if struct_info is not None else (),
                        order=self._component_order_name(args),
                    )
                ),
            }
            return type_meta
        if base_type == BaseType.ENUM:
            enum_name = self._qualified_name_tail(exact_type)
            enum_fqn = self._public_fqn(exact_type) or enum_name
            method_metas: list[MetaValue] = []
            variant_metas: list[MetaValue] = []
            if has_symbol(exact_type, kinds=("enum",)):
                enum_info = self._analyze_enum_by_qualified_name(exact_type)
                method_metas = [
                    self._method_meta_from_info(enum_info, method)
                    for method in enum_info.methods
                    if not method.name.startswith("_")
                ]
                variant_metas = [
                    self._variant_meta_from_info(enum_info, variant)
                    for variant in enum_info.variants
                ]
            type_meta = MetaValue(
                struct_qualified_name=TYPE_META_QNAME,
                fields={
                    "kind": "enum",
                    "name": enum_name,
                    "fqn": enum_fqn,
                    "family_name": enum_name,
                    "family_fqn": enum_fqn,
                    "args": self._type_meta_list([]),
                    "is_named": True,
                    "infer_slots": self._string_meta_list([]),
                },
            )
            type_meta.methods = {
                "methods": self._metadata_list(method_metas, METHOD_META_QNAME),
                "components": self._type_meta_list([]),
                "recursive_components": lambda args: self._type_meta_list([]),
                "variants": self._metadata_list(variant_metas, VARIANT_META_QNAME),
            }
            return type_meta
        if base_type == BaseType.ARRAY:
            args = [
                self._type_meta_from_base(
                    array_info.element_type if array_info else BaseType.UNKNOWN,
                    exact_type=array_info.element_exact_type if array_info else None,
                    tuple_info=array_info.element_tuple_info if array_info else None,
                    callable_info=array_info.element_callable_info if array_info else None,
                    struct_qualified_name=array_info.element_struct_qualified_name if array_info else None,
                    anonymous_struct_info=array_info.element_anonymous_struct_info if array_info else None,
                )
            ]
            return MetaValue(
                struct_qualified_name=TYPE_META_QNAME,
                fields={
                    "kind": "array",
                    "name": f"[{args[0].fields['name']}]",
                    "fqn": f"[{args[0].fields['fqn']}]",
                    "family_name": "array",
                    "family_fqn": "array",
                    "args": self._type_meta_list(args),
                    "is_named": False,
                    "infer_slots": self._string_meta_list([]),
                },
                methods={
                    "fields": self._metadata_list([], FIELD_META_QNAME),
                    "methods": self._metadata_list([], METHOD_META_QNAME),
                    "components": self._type_meta_list([]),
                    "recursive_components": lambda args: self._type_meta_list([]),
                },
            )
        if base_type == BaseType.DICT:
            args = [
                self._type_meta_from_base(
                    dict_info.key_type if dict_info else BaseType.UNKNOWN,
                    exact_type=dict_info.key_exact_type if dict_info else None,
                    callable_info=dict_info.key_callable_info if dict_info else None,
                    struct_qualified_name=dict_info.key_struct_qualified_name if dict_info else None,
                    anonymous_struct_info=dict_info.key_anonymous_struct_info if dict_info else None,
                ),
                self._type_meta_from_base(
                    dict_info.value_type if dict_info else BaseType.UNKNOWN,
                    exact_type=dict_info.value_exact_type if dict_info else None,
                    callable_info=dict_info.value_callable_info if dict_info else None,
                    struct_qualified_name=dict_info.value_struct_qualified_name if dict_info else None,
                    anonymous_struct_info=dict_info.value_anonymous_struct_info if dict_info else None,
                ),
            ]
            name = f"dict<{args[0].fields['name']}, {args[1].fields['name']}>"
            return MetaValue(
                struct_qualified_name=TYPE_META_QNAME,
                fields={
                    "kind": "dict",
                    "name": name,
                    "fqn": name,
                    "family_name": "dict",
                    "family_fqn": "dict",
                    "args": self._type_meta_list(args),
                    "is_named": False,
                    "infer_slots": self._string_meta_list([]),
                },
            )
        if base_type == BaseType.SET:
            args = [
                self._type_meta_from_base(
                    set_info.element_type if set_info else BaseType.UNKNOWN,
                    exact_type=set_info.element_exact_type if set_info else None,
                    struct_qualified_name=set_info.element_struct_qualified_name if set_info else None,
                    anonymous_struct_info=set_info.element_anonymous_struct_info if set_info else None,
                )
            ]
            name = f"set<{args[0].fields['name']}>"
            return MetaValue(
                struct_qualified_name=TYPE_META_QNAME,
                fields={
                    "kind": "set",
                    "name": name,
                    "fqn": name,
                    "family_name": "set",
                    "family_fqn": "set",
                    "args": self._type_meta_list(args),
                    "is_named": False,
                    "infer_slots": self._string_meta_list([]),
                },
            )
        if base_type == BaseType.TUPLE:
            args = []
            if tuple_info is not None:
                for index, element_type in enumerate(tuple_info.element_types):
                    args.append(
                        self._type_meta_from_base(
                            element_type,
                            exact_type=tuple_info.element_exact_types[index]
                            if index < len(tuple_info.element_exact_types)
                            else None,
                            tuple_info=tuple_info.element_tuple_infos.get(index),
                            callable_info=tuple_info.element_callable_infos.get(index),
                            struct_qualified_name=tuple_info.element_struct_qualified_names.get(index),
                            anonymous_struct_info=tuple_info.element_anonymous_struct_infos.get(index),
                        )
                    )
            rendered = ", ".join(str(arg.fields["name"]) for arg in args)
            return MetaValue(
                struct_qualified_name=TYPE_META_QNAME,
                fields={
                    "kind": "tuple",
                    "name": f"({rendered})",
                    "fqn": f"({rendered})",
                    "family_name": "tuple",
                    "family_fqn": "tuple",
                    "args": self._type_meta_list(args),
                    "is_named": False,
                    "infer_slots": self._string_meta_list([]),
                },
            )
        if base_type == BaseType.CHANNEL:
            args = []
            if callable_info is not None:
                args = []
            return MetaValue(
                struct_qualified_name=TYPE_META_QNAME,
                fields={
                    "kind": "channel",
                    "name": "channel",
                    "fqn": "channel",
                    "family_name": "channel",
                    "family_fqn": "channel",
                    "args": self._type_meta_list(args),
                    "is_named": False,
                    "infer_slots": self._string_meta_list([]),
                },
            )
        if base_type == BaseType.CALLABLE:
            return MetaValue(
                struct_qualified_name=TYPE_META_QNAME,
                fields={
                    "kind": "callable",
                    "name": callable_info.rust_type_name() if callable_info else "callable",
                    "fqn": callable_info.rust_type_name() if callable_info else "callable",
                    "family_name": "callable",
                    "family_fqn": "callable",
                    "args": self._type_meta_list([]),
                    "is_named": False,
                    "infer_slots": self._string_meta_list([]),
                },
            )
        exact = exact_type or default_exact_type(base_type) or type_to_rust(base_type)
        return MetaValue(
            struct_qualified_name=TYPE_META_QNAME,
            fields={
                "kind": self._struct_type_kind_name(exact),
                "name": exact,
                "fqn": exact,
                "family_name": exact,
                "family_fqn": exact,
                "args": self._type_meta_list([]),
                "is_named": True,
                "infer_slots": self._string_meta_list([]),
            },
        )

    def _type_meta_from_value_info(self, info: ResolvedValueInfo) -> MetaValue:
        """Return TypeMeta for a resolved value description."""
        return self._type_meta_from_base(
            info.base_type,
            exact_type=info.exact_type,
            array_info=info.array_info,
            dict_info=info.dict_info,
            set_info=info.set_info,
            tuple_info=info.tuple_info,
            callable_info=info.callable_info,
            struct_qualified_name=info.struct_qualified_name,
            anonymous_struct_info=info.anonymous_struct_info,
        )

    def _type_meta_from_symbol(self, symbol: Symbol | None) -> MetaValue:
        """Return TypeMeta for a resolved symbol."""
        if symbol is None:
            return unknown_type_meta()
        return self._type_meta_from_value_info(self._value_info_from_symbol(symbol.resolved_type, symbol))

    def _type_meta_from_path(self, path: list[str]) -> MetaValue | None:
        """Resolve a type-symbol path into TypeMeta."""
        if not path:
            return None
        exact_scalar = self._exact_type_name_from_text(".".join(path))
        if exact_scalar is not None and exact_type_to_base(exact_scalar) != BaseType.UNKNOWN:
            return self._type_meta_from_base(exact_type_to_base(exact_scalar), exact_type=exact_scalar)
        if path == ["ComponentOrder"]:
            return self._type_meta_from_base(BaseType.ENUM, exact_type=COMPONENT_ORDER_QNAME)
        if self._current_module is None:
            return None
        struct_symbol = self.module_graph.resolve_struct_path(self._current_module, path)
        if struct_symbol is not None:
            return self._type_meta_from_base(BaseType.STRUCT, struct_qualified_name=struct_symbol.qualified_name)
        enum_symbol = self.module_graph.resolve_enum_path(self._current_module, path)
        if enum_symbol is not None:
            return self._type_meta_from_base(BaseType.ENUM, exact_type=enum_symbol.qualified_name)
        return None

    def _component_order_name(self, args: list[object]) -> str:
        """Decode the recursive_components ordering argument."""
        if not args:
            return "depth_first"
        order = args[0]
        if isinstance(order, MetaValue) and order.struct_qualified_name == COMPONENT_ORDER_QNAME:
            return str(order.fields.get("name", "depth_first"))
        if isinstance(order, str):
            return order
        return "depth_first"

    def _recursive_component_type_metas(
        self,
        source_names: tuple[str, ...],
        *,
        order: str,
    ) -> list[MetaValue]:
        """Return recursive component TypeMeta values in a stable order."""
        seen: set[str] = set()
        result: list[str] = []

        def dfs(name: str) -> None:
            if name in seen:
                return
            seen.add(name)
            result.append(name)
            struct_info = self.atlas.structs.get(name)
            if struct_info is None:
                return
            for child in struct_info.composition_sources:
                dfs(child)

        def bfs(initial: tuple[str, ...]) -> None:
            queue = list(initial)
            while queue:
                name = queue.pop(0)
                if name in seen:
                    continue
                seen.add(name)
                result.append(name)
                struct_info = self.atlas.structs.get(name)
                if struct_info is None:
                    continue
                queue.extend(struct_info.composition_sources)

        if order == "breadth_first":
            bfs(source_names)
        else:
            for name in source_names:
                dfs(name)
        if order == "topological":
            result = list(reversed(result))
        return [self._type_meta_from_base(BaseType.STRUCT, struct_qualified_name=name) for name in result]

    def _struct_meta_from_qualified_name(self, qualified_name: str) -> MetaValue:
        """Return StructMeta for a named struct."""
        symbol = self.module_graph.get_symbol(qualified_name)
        struct_meta = MetaValue(
            struct_qualified_name=STRUCT_META_QNAME,
            fields={
                **self._base_meta_fields(
                    kind="struct",
                    name=symbol.name,
                    fqn=self._public_fqn(symbol.qualified_name),
                    module_fqn=symbol.module_id,
                    file=self._module_source_file(symbol.module_id),
                    line_num=symbol.ctx.start.line if symbol.ctx.start is not None else 0,
                    is_public=symbol.is_public,
                ),
                "type_info": self._type_meta_from_base(
                    BaseType.STRUCT,
                    struct_qualified_name=qualified_name,
                ),
            },
        )
        return struct_meta

    def _enum_meta_from_qualified_name(self, qualified_name: str) -> MetaValue:
        """Return EnumMeta for a named enum."""
        symbol = self.module_graph.get_symbol(qualified_name)
        enum_meta = MetaValue(
            struct_qualified_name=ENUM_META_QNAME,
            fields={
                **self._base_meta_fields(
                    kind="enum",
                    name=symbol.name,
                    fqn=self._public_fqn(symbol.qualified_name),
                    module_fqn=symbol.module_id,
                    file=self._module_source_file(symbol.module_id),
                    line_num=symbol.ctx.start.line if symbol.ctx.start is not None else 0,
                    is_public=symbol.is_public,
                ),
                "type_info": self._type_meta_from_base(
                    BaseType.ENUM,
                    exact_type=qualified_name,
                ),
            },
        )
        return enum_meta

    def _field_meta_from_info(
        self,
        owner: StructInstance,
        field: StructFieldInfo,
        index: int,
    ) -> MetaValue:
        """Return FieldMeta for one effective struct field."""
        is_declared = field.source_struct_qualified_name == owner.qualified_name
        source_component_fqn = ""
        if not is_declared and field.source_struct_qualified_name is not None:
            source_component_fqn = self._public_fqn(field.source_struct_qualified_name)
        field_meta = MetaValue(
            struct_qualified_name=FIELD_META_QNAME,
            fields={
                **self._base_meta_fields(
                    kind="field",
                    name=field.name,
                    fqn=f"{self._public_fqn(owner.qualified_name)}/{field.name}",
                    module_fqn=owner.module_id,
                    file=self._module_source_file(owner.module_id),
                    line_num=field.line_num,
                    is_public=not field.is_private,
                ),
                "value_type": self._type_meta_from_base(
                    field.resolved_type,
                    exact_type=field.exact_type,
                    array_info=field.array_info,
                    dict_info=field.dict_info,
                    set_info=field.set_info,
                    tuple_info=field.tuple_info,
                    callable_info=field.callable_info,
                    struct_qualified_name=field.struct_qualified_name,
                    anonymous_struct_info=field.anonymous_struct_info,
                ),
                "index": index,
                "is_const": field.is_const,
                "has_default": field.default_value is not None,
                "is_declared": is_declared,
                "source_component_fqn": source_component_fqn,
            },
        )
        field_meta.methods = {
            "owner": lambda args: self._struct_meta_from_qualified_name(owner.qualified_name),
        }
        return field_meta

    def _function_parameter_meta_from_ctx(
        self,
        owner_qualified_name: str,
        owner_module_id: str,
        param_ctx,
        index: int,
        *,
        owner_meta: MetaValue,
    ) -> MetaValue:
        """Return FunctionParameterMeta for a top-level function parameter."""
        param_type = self._type_meta_from_path(param_ctx.type_().getText().split(".")) if param_ctx.type_() else unknown_type_meta()
        declared_type = param_type if param_ctx.type_() else unknown_type_meta()
        meta = MetaValue(
            struct_qualified_name=FUNCTION_PARAM_META_QNAME,
            fields={
                **self._base_meta_fields(
                    kind="parameter",
                    name=param_ctx.IDENTIFIER().getText(),
                    fqn=f"{self._public_fqn(owner_qualified_name)}/{param_ctx.IDENTIFIER().getText()}",
                    module_fqn=owner_module_id,
                    file=self._module_source_file(owner_module_id),
                    line_num=param_ctx.start.line if param_ctx.start is not None else 0,
                    is_public=False,
                ),
                "index": index,
                "value_type": param_type,
                "declared_type": declared_type,
                "has_declared_type": param_ctx.type_() is not None,
            },
        )
        meta.methods = {"owner": lambda args: owner_meta}
        return meta

    def _method_parameter_meta_from_info(
        self,
        owner_qualified_name: str,
        owner_module_id: str,
        param: tuple[str, str | None, str | None],
        index: int,
        *,
        owner_meta: MetaValue,
    ) -> MetaValue:
        """Return MethodParameterMeta for an analyzed method parameter."""
        name, type_ann, resolved = param
        declared_type = self._resolved_named_type_info(
            resolved or type_ann,
            source_module_id=owner_module_id,
            owner_qualified_name=owner_qualified_name,
            owner_kind="struct",
        )
        value_type = self._type_meta_from_value_info(declared_type)
        meta = MetaValue(
            struct_qualified_name=METHOD_PARAM_META_QNAME,
            fields={
                **self._base_meta_fields(
                    kind="parameter",
                    name=name,
                    fqn=f"{self._public_fqn(owner_qualified_name)}/{owner_meta.fields['name']}/{name}",
                    module_fqn=owner_module_id,
                    file=self._module_source_file(owner_module_id),
                    line_num=int(owner_meta.fields.get("line_num", 0)),
                    is_public=False,
                ),
                "index": index,
                "value_type": value_type,
                "declared_type": value_type if type_ann or resolved else unknown_type_meta(),
                "has_declared_type": bool(type_ann),
            },
        )
        meta.methods = {"owner": lambda args: owner_meta}
        return meta

    def _function_meta_from_qualified_name(self, qualified_name: str) -> MetaValue:
        """Return FunctionMeta for a top-level function declaration."""
        symbol = self.module_graph.get_symbol(qualified_name)
        function_meta = MetaValue(
            struct_qualified_name=FUNCTION_META_QNAME,
            fields={
                **self._base_meta_fields(
                    kind="function",
                    name=symbol.name,
                    fqn=self._public_fqn(symbol.qualified_name),
                    module_fqn=symbol.module_id,
                    file=self._module_source_file(symbol.module_id),
                    line_num=symbol.ctx.start.line if symbol.ctx.start is not None else 0,
                    is_public=symbol.is_public,
                ),
                "params": self._metadata_list([], FUNCTION_PARAM_META_QNAME),
                "return_type": unknown_type_meta(),
                "is_async": isinstance(symbol.ctx, ZincParser.AsyncFunctionDeclarationContext),
                "is_generator": False,
            },
        )
        params: list[MetaValue] = []
        if hasattr(symbol.ctx, "parameterList") and symbol.ctx.parameterList():
            params = [
                self._function_parameter_meta_from_ctx(
                    qualified_name,
                    symbol.module_id,
                    param_ctx,
                    index,
                    owner_meta=function_meta,
                )
                for index, param_ctx in enumerate(symbol.ctx.parameterList().parameter())
            ]
        function_meta.fields["params"] = self._metadata_list(params, FUNCTION_PARAM_META_QNAME)
        return function_meta

    def _method_meta_from_info(
        self,
        owner: StructInstance | EnumInstance,
        method: StructMethodInfo,
    ) -> MetaValue:
        """Return MethodMeta for an effective struct or enum method."""
        is_declared = method.source_struct_qualified_name == owner.qualified_name
        method_meta = MetaValue(
            struct_qualified_name=METHOD_META_QNAME,
            fields={
                **self._base_meta_fields(
                    kind="method",
                    name=method.name,
                    fqn=f"{self._public_fqn(owner.qualified_name)}/{method.name}",
                    module_fqn=owner.module_id,
                    file=self._module_source_file(owner.module_id),
                    line_num=method.line_num,
                    is_public=not method.name.startswith("_"),
                ),
                "params": self._metadata_list([], METHOD_PARAM_META_QNAME),
                "return_type": self._type_meta_from_value_info(
                    self._resolved_named_type_info(
                        method.return_type,
                        source_module_id=method.source_module_id or owner.module_id,
                        owner_qualified_name=owner.qualified_name,
                        owner_kind="enum" if isinstance(owner, EnumInstance) else "struct",
                    )
                ),
                "is_async": False,
                "is_generator": False,
                "is_static": method.is_static,
                "is_declared": is_declared,
            },
        )
        params = [
            self._method_parameter_meta_from_info(
                owner.qualified_name,
                owner.module_id,
                param,
                index,
                owner_meta=method_meta,
            )
            for index, param in enumerate(method.parameters)
        ]
        method_meta.fields["params"] = self._metadata_list(params, METHOD_PARAM_META_QNAME)
        if isinstance(owner, EnumInstance):
            method_meta.methods = {"owner": lambda args: self._enum_meta_from_qualified_name(owner.qualified_name)}
        else:
            method_meta.methods = {"owner": lambda args: self._struct_meta_from_qualified_name(owner.qualified_name)}
        return method_meta

    def _variant_meta_from_info(
        self,
        owner: EnumInstance,
        variant: EnumVariantInfo,
    ) -> MetaValue:
        """Return VariantMeta for an enum variant."""
        variant_meta = MetaValue(
            struct_qualified_name=VARIANT_META_QNAME,
            fields={
                **self._base_meta_fields(
                    kind="variant",
                    name=variant.name,
                    fqn=f"{self._public_fqn(owner.qualified_name)}/{variant.name}",
                    module_fqn=owner.module_id,
                    file=self._module_source_file(owner.module_id),
                    line_num=variant.line_num,
                    is_public=True,
                ),
                "index": variant.index,
            },
        )
        variant_meta.methods = {"owner": lambda args: self._enum_meta_from_qualified_name(owner.qualified_name)}
        return variant_meta

    def _builtin_meta_from_name(self, name: str) -> MetaValue:
        """Return BuiltinMeta for a built-in function."""
        return MetaValue(
            struct_qualified_name=BUILTIN_META_QNAME,
            fields={
                **self._base_meta_fields(
                    kind="builtin",
                    name=name,
                    fqn=f"builtin/{name}",
                    module_fqn="builtin",
                    file="",
                    line_num=0,
                    is_public=True,
                ),
                "params": self._metadata_list([], FUNCTION_PARAM_META_QNAME),
                "return_type": unknown_type_meta(),
                "is_async": False,
                "is_generator": False,
            },
        )

    def _const_meta_from_qualified_name(self, qualified_name: str) -> MetaValue:
        """Return ConstMeta for a top-level const."""
        const = self.atlas.consts.get(qualified_name)
        symbol = self.module_graph.get_symbol(qualified_name)
        resolved = self.symbols.lookup_by_id(qualified_name)
        return MetaValue(
            struct_qualified_name=CONST_META_QNAME,
            fields={
                **self._base_meta_fields(
                    kind="const",
                    name=symbol.name,
                    fqn=self._public_fqn(qualified_name),
                    module_fqn=symbol.module_id,
                    file=self._module_source_file(symbol.module_id),
                    line_num=symbol.ctx.start.line if symbol.ctx.start is not None else 0,
                    is_public=symbol.is_public,
                ),
                "value_type": self._type_meta_from_symbol(resolved),
                "value_text": const.ctx.expression().getText() if const is not None else "",
            },
        )

    def _current_owner_meta(self) -> MetaValue:
        """Return metadata for the current function-like owner."""
        if self._current_function and self._current_function in self.atlas.functions:
            return self._function_meta_from_qualified_name(
                self.atlas.functions[self._current_function].qualified_name
            )
        return MetaValue(
            struct_qualified_name=FUNCTION_META_QNAME,
            fields={
                **self._base_meta_fields(
                    kind="function",
                    name=self._current_owner_name(),
                    fqn=self._current_owner_fqn(),
                    module_fqn=self._current_module or "",
                    file=self._module_source_file(self._current_module),
                    line_num=0,
                    is_public=False,
                ),
                "params": self._metadata_list([], FUNCTION_PARAM_META_QNAME),
                "return_type": unknown_type_meta(),
                "is_async": False,
                "is_generator": False,
            },
        )

    def _variable_meta_from_symbol(self, symbol: Symbol) -> MetaValue:
        """Return VariableMeta or parameter-style meta for a local binding."""
        owner_meta = self._current_owner_meta()
        base_fields = self._base_meta_fields(
            kind="variable" if symbol.kind == SymbolKind.VARIABLE else "parameter",
            name=symbol.id or "",
            fqn=f"{self._current_owner_fqn()}/{symbol.id or symbol.unique_name}",
            module_fqn=self._current_module or "",
            file=self._module_source_file(self._current_module),
            line_num=symbol.line_num,
            is_public=False,
        )
        if symbol.kind == SymbolKind.PARAMETER:
            struct_qname = FUNCTION_PARAM_META_QNAME
            fields = {
                **base_fields,
                "index": 0,
                "value_type": self._type_meta_from_symbol(symbol),
                "declared_type": self._type_meta_from_base(
                    exact_type_to_base(symbol.declared_exact_type),
                    exact_type=symbol.declared_exact_type,
                )
                if symbol.has_declared_type
                else unknown_type_meta(),
                "has_declared_type": symbol.has_declared_type,
            }
        else:
            struct_qname = VARIABLE_META_QNAME
            fields = {
                **base_fields,
                "value_type": self._type_meta_from_symbol(symbol),
                "has_declared_type": symbol.has_declared_type,
                "is_mutated": symbol.is_mutated,
                "is_shadow": symbol.is_shadow,
            }
        meta = MetaValue(
            struct_qualified_name=struct_qname,
            fields=fields,
        )
        meta.methods = {"owner": lambda args: owner_meta}
        return meta

    def _meta_from_expression(self, expr_ctx) -> MetaValue:
        """Resolve meta(expr) for one named program entity."""
        if isinstance(expr_ctx, ZincParser.PrimaryExprContext):
            primary = expr_ctx.primaryExpression()
            if primary and primary.IDENTIFIER():
                name = primary.IDENTIFIER().getText()
                symbol = self.symbols.lookup_by_id(name)
                if symbol is not None:
                    if symbol.kind in {SymbolKind.VARIABLE, SymbolKind.PARAMETER}:
                        return self._variable_meta_from_symbol(symbol)
                    if symbol.kind == SymbolKind.BUILTIN:
                        return self._builtin_meta_from_name(name)
                if self._current_module is not None:
                    resolved_const = self.module_graph.resolve_const_path(self._current_module, [name])
                    if resolved_const is not None:
                        return self._const_meta_from_qualified_name(resolved_const.qualified_name)
                    resolved_struct = self.module_graph.resolve_struct_path(self._current_module, [name])
                    if resolved_struct is not None:
                        return self._struct_meta_from_qualified_name(resolved_struct.qualified_name)
                    resolved_enum = self.module_graph.resolve_enum_path(self._current_module, [name])
                    if resolved_enum is not None:
                        return self._enum_meta_from_qualified_name(resolved_enum.qualified_name)
                    resolved_function = self.module_graph.resolve_function_path(self._current_module, [name])
                    if resolved_function is not None:
                        return self._function_meta_from_qualified_name(resolved_function.qualified_name)
                raise ZincTypeError(f"meta() could not resolve symbol '{name}'")
        if isinstance(expr_ctx, ZincParser.MemberAccessExprContext) and self._current_module is not None:
            path = extract_identifier_path(expr_ctx)
            if path:
                static_target = self.module_graph.resolve_static_method_target(self._current_module, path)
                if static_target is not None:
                    owner_symbol, method_name = static_target
                    if owner_symbol.kind == "struct":
                        owner = self._analyze_struct_by_qualified_name(owner_symbol.qualified_name)
                    else:
                        owner = self._analyze_enum_by_qualified_name(owner_symbol.qualified_name)
                    method = next((item for item in owner.methods if item.name == method_name), None)
                    if method is not None:
                        return self._method_meta_from_info(owner, method)
                variant_target = self.module_graph.resolve_enum_variant_path(self._current_module, path)
                if variant_target is not None:
                    enum_symbol, variant_name = variant_target
                    enum_info = self._analyze_enum_by_qualified_name(enum_symbol.qualified_name)
                    variant = next((item for item in enum_info.variants if item.name == variant_name), None)
                    if variant is None:
                        raise ZincTypeError(f"unknown enum variant '{'.'.join(path)}'")
                    return self._variant_meta_from_info(enum_info, variant)
            receiver_symbol = self._expr_symbol(expr_ctx.expression())
            if receiver_symbol is None:
                receiver_path = extract_identifier_path(expr_ctx.expression())
                if receiver_path and len(receiver_path) == 1:
                    receiver_symbol = self.symbols.lookup_by_id(receiver_path[0])
            receiver_struct_name = self._struct_qualified_name_for_symbol(receiver_symbol)
            if receiver_struct_name and receiver_struct_name in self.atlas.structs:
                struct_info = self._analyze_struct_by_qualified_name(receiver_struct_name)
                field = next((item for item in struct_info.fields if item.name == expr_ctx.IDENTIFIER().getText()), None)
                if field is not None:
                    return self._field_meta_from_info(
                        struct_info,
                        field,
                        struct_info.fields.index(field),
                    )
                method = next((item for item in struct_info.methods if item.name == expr_ctx.IDENTIFIER().getText()), None)
                if method is not None:
                    return self._method_meta_from_info(struct_info, method)
        raise ZincTypeError("meta() expects a symbol, field, method, type, or enum variant")

    def _has_component_named(self, actual_qualified_name: str | None, expected_qualified_name: str | None) -> bool:
        """Return True when one struct recursively composes another."""
        if actual_qualified_name is None or expected_qualified_name is None:
            return False
        if actual_qualified_name == expected_qualified_name:
            return True
        try:
            symbol = self.module_graph.get_symbol(actual_qualified_name)
        except KeyError:
            return False
        if symbol.kind != "struct":
            return False
        struct_info = self._analyze_struct_by_qualified_name(actual_qualified_name)
        for component_name in struct_info.composition_sources:
            if self._has_component_named(component_name, expected_qualified_name):
                return True
        return False

    def _has_component_from_types(self, actual: MetaValue, expected: MetaValue) -> bool:
        """Return True when actual recursively composes expected."""
        return self._has_component_named(
            str(actual.fields.get("family_fqn", "")).replace("/", "::"),
            str(expected.fields.get("family_fqn", "")).replace("/", "::"),
        )

    def _implements_from_types(self, actual: MetaValue, expected: MetaValue) -> bool:
        """Return True when actual structurally implements expected."""
        if self._has_component_from_types(actual, expected):
            return True

        def is_unknown_type_meta(value: object) -> bool:
            return (
                isinstance(value, MetaValue)
                and value.struct_qualified_name == TYPE_META_QNAME
                and value.fields.get("kind") == "unknown"
            )

        expected_fields = {
            str(field.fields["name"]): field
            for field in expected.call_method("fields", []).items
            if isinstance(field, MetaValue) and bool(field.fields.get("is_public", False))
        } if expected.has_method("fields") else {}
        actual_fields = {
            str(field.fields["name"]): field
            for field in actual.call_method("fields", []).items
            if isinstance(field, MetaValue) and bool(field.fields.get("is_public", False))
        } if actual.has_method("fields") else {}
        for name, field_meta in expected_fields.items():
            actual_field = actual_fields.get(name)
            if actual_field is None:
                return False
            expected_type = field_meta.fields.get("value_type")
            if not is_unknown_type_meta(expected_type) and actual_field.fields.get("value_type") != expected_type:
                return False
        expected_methods = {
            str(method.fields["name"]): method
            for method in expected.call_method("methods", []).items
            if isinstance(method, MetaValue)
            and bool(method.fields.get("is_public", False))
            and not bool(method.fields.get("is_static", False))
        } if expected.has_method("methods") else {}
        actual_methods = {
            str(method.fields["name"]): method
            for method in actual.call_method("methods", []).items
            if isinstance(method, MetaValue)
            and bool(method.fields.get("is_public", False))
            and not bool(method.fields.get("is_static", False))
        } if actual.has_method("methods") else {}
        for name, method_meta in expected_methods.items():
            actual_method = actual_methods.get(name)
            if actual_method is None:
                return False
            expected_params = method_meta.fields.get("params")
            actual_params = actual_method.fields.get("params")
            if isinstance(expected_params, MetaListValue) and isinstance(actual_params, MetaListValue):
                if len(expected_params.items) != len(actual_params.items):
                    return False
                for expected_param, actual_param in zip(expected_params.items, actual_params.items):
                    if not isinstance(expected_param, MetaValue) or not isinstance(actual_param, MetaValue):
                        return False
                    if bool(expected_param.fields.get("has_declared_type", False)):
                        expected_declared = expected_param.fields.get("declared_type")
                        if (
                            not is_unknown_type_meta(expected_declared)
                            and actual_param.fields.get("value_type") != expected_declared
                        ):
                            return False
            expected_return = method_meta.fields.get("return_type")
            if (
                isinstance(expected_return, MetaValue)
                and not is_unknown_type_meta(expected_return)
                and actual_method.fields.get("return_type") != expected_return
            ):
                return False
        return True

    def _type_meta_from_expr_ctx(self, expr_ctx) -> MetaValue:
        """Resolve type(expr) for either a value expression or a type symbol."""
        path = extract_identifier_path(expr_ctx)
        if path:
            local_symbol = None
            if len(path) == 1:
                local_symbol = self.symbols.lookup_by_id(path[0])
            if local_symbol is None:
                type_meta = self._type_meta_from_path(path)
                if type_meta is not None:
                    return type_meta
                if path[0] == "ComponentOrder" and len(path) == 2 and path[1] in COMPONENT_ORDER_VARIANTS:
                    return self._type_meta_from_base(BaseType.ENUM, exact_type=COMPONENT_ORDER_QNAME)
        return self._type_meta_from_value_info(self._value_info_from_expression(expr_ctx))

    def _attribute_constraint_exprs(self, ctx) -> list:
        """Return all constraint expressions attached to one declaration."""
        getter = getattr(ctx, "attributeBlock", None)
        if getter is None:
            return []
        exprs = []
        for block in getter():
            exprs.extend(list(block.expression()))
        return exprs

    def _evaluate_constraint_expr(self, expr_ctx, slots: dict[str, MetaValue]):
        """Evaluate a compile-time constraint expression."""
        if expr_ctx is None:
            return None
        if isinstance(expr_ctx, ZincParser.PrimaryExprContext):
            return self._evaluate_constraint_expr(expr_ctx.primaryExpression(), slots)
        if isinstance(expr_ctx, ZincParser.PrimaryExpressionContext):
            if expr_ctx.literal():
                text = expr_ctx.literal().getText()
                return self._parse_constant_literal(text)
            if expr_ctx.arrayLiteral():
                return [
                    self._evaluate_constraint_expr(item, slots)
                    for item in expr_ctx.arrayLiteral().expression()
                ]
            if expr_ctx.IDENTIFIER():
                name = expr_ctx.IDENTIFIER().getText()
                if name in slots:
                    return slots[name]
                type_meta = self._type_meta_from_path([name])
                if type_meta is not None:
                    return type_meta
                return name
        if isinstance(expr_ctx, ZincParser.ArrayLiteralContext):
            return [self._evaluate_constraint_expr(item, slots) for item in expr_ctx.expression()]
        if isinstance(expr_ctx, ZincParser.MemberAccessExprContext):
            receiver = self._evaluate_constraint_expr(expr_ctx.expression(), slots)
            member_name = expr_ctx.IDENTIFIER().getText()
            if isinstance(receiver, MetaValue):
                if receiver.has_field(member_name):
                    return receiver.get_field(member_name)
                if receiver.has_method(member_name):
                    return ("__meta_method__", receiver, member_name)
            if isinstance(receiver, str) and receiver == "ComponentOrder" and member_name in COMPONENT_ORDER_VARIANTS:
                return component_order_value(member_name)
            raise ZincTypeError(f"unsupported constraint member access '{expr_ctx.getText()}'")
        if isinstance(expr_ctx, ZincParser.IndexAccessExprContext):
            target = self._evaluate_constraint_expr(expr_ctx.expression(0), slots)
            index = self._evaluate_constraint_expr(expr_ctx.expression(1), slots)
            if isinstance(target, MetaListValue):
                return target.items[index]
            return target[index]
        if isinstance(expr_ctx, ZincParser.FunctionCallExprContext):
            callee = expr_ctx.expression()
            args = [self._evaluate_constraint_expr(arg, slots) for arg in expr_ctx.argumentList().expression()] if expr_ctx.argumentList() else []
            if isinstance(callee, ZincParser.PrimaryExprContext):
                primary = callee.primaryExpression()
                if primary and primary.IDENTIFIER():
                    func_name = primary.IDENTIFIER().getText()
                    if func_name == "type":
                        if len(args) != 1:
                            raise ZincTypeError("constraint type() expects one argument")
                        value = args[0]
                        if isinstance(value, MetaValue) and value.struct_qualified_name == TYPE_META_QNAME:
                            return value
                        if isinstance(value, MetaValue):
                            return self._type_meta_from_base(BaseType.STRUCT, struct_qualified_name=value.struct_qualified_name)
                        raise ZincTypeError("constraint type() expects a constrained slot or type symbol")
                    if func_name == "has_component":
                        if len(args) != 2 or not all(isinstance(arg, MetaValue) for arg in args):
                            raise ZincTypeError("constraint has_component() expects two type operands")
                        return self._has_component_from_types(args[0], args[1])
                    if func_name == "implements":
                        if len(args) != 2 or not all(isinstance(arg, MetaValue) for arg in args):
                            raise ZincTypeError("constraint implements() expects two type operands")
                        return self._implements_from_types(args[0], args[1])
            callee_value = self._evaluate_constraint_expr(callee, slots)
            if (
                isinstance(callee_value, tuple)
                and len(callee_value) == 3
                and callee_value[0] == "__meta_method__"
            ):
                _tag, meta_value, method_name = callee_value
                return meta_value.call_method(method_name, args)
            raise ZincTypeError(f"unsupported constraint call '{expr_ctx.getText()}'")
        if isinstance(expr_ctx, ZincParser.ParenExprContext):
            return self._evaluate_constraint_expr(expr_ctx.expression(), slots)
        if isinstance(expr_ctx, ZincParser.UnaryExprContext):
            operand = self._evaluate_constraint_expr(expr_ctx.expression(), slots)
            op = expr_ctx.getChild(0).getText()
            if op in {"!", "not"}:
                return not operand
            if op == "-":
                return -operand
        if isinstance(expr_ctx, ZincParser.EqualityExprContext):
            left = self._evaluate_constraint_expr(expr_ctx.expression(0), slots)
            right = self._evaluate_constraint_expr(expr_ctx.expression(1), slots)
            return left == right if expr_ctx.getChild(1).getText() == "==" else left != right
        if isinstance(expr_ctx, ZincParser.MembershipExprContext):
            left = self._evaluate_constraint_expr(expr_ctx.expression(0), slots)
            right = self._evaluate_constraint_expr(expr_ctx.expression(1), slots)
            if isinstance(right, MetaListValue):
                return left in right.items
            return left in right
        if isinstance(expr_ctx, ZincParser.LogicalAndExprContext):
            return bool(
                self._evaluate_constraint_expr(expr_ctx.expression(0), slots)
                and self._evaluate_constraint_expr(expr_ctx.expression(1), slots)
            )
        if isinstance(expr_ctx, ZincParser.LogicalOrExprContext):
            return bool(
                self._evaluate_constraint_expr(expr_ctx.expression(0), slots)
                or self._evaluate_constraint_expr(expr_ctx.expression(1), slots)
            )
        raise ZincTypeError(f"unsupported constraint expression '{expr_ctx.getText()}'")

    def _validate_constraints(self, ctx, slots: dict[str, MetaValue], *, label: str) -> None:
        """Validate every attached attribute constraint for one declaration/use site."""
        for expr_ctx in self._attribute_constraint_exprs(ctx):
            if not self._evaluate_constraint_expr(expr_ctx, slots):
                raise ZincTypeError(f"{label} constraint failed: {expr_ctx.getText()}")

    def _constraint_slots_from_call(
        self,
        ctx,
        arg_types: list[BaseType],
        arg_exact_types: list[str | None],
        arg_array_infos: dict[int, ArrayTypeInfo],
        arg_dict_infos: dict[int, DictTypeInfo],
        arg_set_infos: dict[int, SetTypeInfo],
        arg_tuple_infos: dict[int, TupleTypeInfo],
        arg_callable_infos: dict[int, CallableTypeInfo],
        arg_struct_qualified_names: dict[int, str],
        arg_anonymous_struct_infos: dict[int, AnonymousStructTypeInfo],
    ) -> dict[str, MetaValue]:
        """Build the slot->TypeMeta environment for parameter constraints."""
        slots: dict[str, MetaValue] = {}
        if not hasattr(ctx, "parameterList") or ctx.parameterList() is None:
            return slots
        for index, param_ctx in enumerate(ctx.parameterList().parameter()):
            if index >= len(arg_types):
                continue
            slots[param_ctx.IDENTIFIER().getText()] = self._type_meta_from_base(
                arg_types[index],
                exact_type=arg_exact_types[index] if index < len(arg_exact_types) else None,
                array_info=arg_array_infos.get(index),
                dict_info=arg_dict_infos.get(index),
                set_info=arg_set_infos.get(index),
                tuple_info=arg_tuple_infos.get(index),
                callable_info=arg_callable_infos.get(index),
                struct_qualified_name=arg_struct_qualified_names.get(index),
                anonymous_struct_info=arg_anonymous_struct_infos.get(index),
            )
        return slots

    def _require_boolean_condition(self, expr_ctx, label: str = "if condition") -> None:
        """Require a condition expression to resolve to bool, refining unknown bindings when possible."""
        expr_type = self.visit(expr_ctx)
        if expr_type == BaseType.BOOLEAN:
            return

        expr_symbol = self._expr_symbol(expr_ctx)
        binding_symbol = None
        if isinstance(expr_ctx, ZincParser.PrimaryExprContext):
            primary = expr_ctx.primaryExpression()
            if primary and primary.IDENTIFIER():
                binding_symbol = self.symbols.lookup_by_id(primary.IDENTIFIER().getText())

        refined = False
        for symbol in (binding_symbol, expr_symbol):
            if symbol is not None and symbol.resolved_type == BaseType.UNKNOWN:
                symbol.resolved_type = BaseType.BOOLEAN
                refined = True

        if refined:
            return

        raise ZincTypeError(f"{label} must be a bool")

    def _merge_array_info(
        self,
        current: ArrayTypeInfo | None,
        incoming: ArrayTypeInfo | None,
        label: str,
    ) -> ArrayTypeInfo | None:
        """Merge array element metadata across multiple value paths."""
        if incoming is None:
            return current
        if current is None:
            return self._copy_array_info(incoming)

        if current.element_type == BaseType.UNKNOWN:
            current.element_type = incoming.element_type
            current.element_exact_type = incoming.element_exact_type
        elif incoming.element_type != BaseType.UNKNOWN and current.element_type != incoming.element_type:
            merged = promote_numeric(current.element_type, incoming.element_type)
            if merged == BaseType.UNKNOWN:
                raise ZincTypeError(f"{label} have incompatible array element types")
            current.element_type = merged
            current.element_exact_type = self._merge_exact_type_for_base(
                current.element_exact_type,
                incoming.element_exact_type,
                merged,
                f"{label} have incompatible array element types",
            )
        else:
            current.element_exact_type = self._merge_exact_type_for_base(
                current.element_exact_type,
                incoming.element_exact_type,
                current.element_type,
                f"{label} have incompatible array element types",
            )

        if current.element_type == BaseType.TUPLE:
            current.element_tuple_info = self._merge_tuple_info(
                current.element_tuple_info,
                incoming.element_tuple_info,
            )
        if current.element_type == BaseType.CALLABLE:
            current.element_callable_info = self._merge_callable_info(
                current.element_callable_info,
                incoming.element_callable_info,
                "array element",
            )
        if current.element_type == BaseType.STRUCT:
            if (
                current.element_struct_qualified_name is not None
                or current.element_anonymous_struct_info is not None
            ) and not self._structs_compatible(
                current.element_struct_qualified_name,
                current.element_anonymous_struct_info,
                incoming.element_struct_qualified_name,
                incoming.element_anonymous_struct_info,
            ):
                raise ZincTypeError(f"{label} have incompatible array element types")
            if current.element_struct_qualified_name is None:
                current.element_struct_qualified_name = incoming.element_struct_qualified_name
            if current.element_anonymous_struct_info is None and incoming.element_anonymous_struct_info is not None:
                current.element_anonymous_struct_info = self._copy_anonymous_struct_info(
                    incoming.element_anonymous_struct_info
                )

        return current

    def _merge_channel_info(
        self,
        current: ChannelTypeInfo | None,
        incoming: ChannelTypeInfo | None,
        label: str,
    ) -> ChannelTypeInfo | None:
        """Merge channel payload metadata across multiple value paths."""
        if incoming is None:
            return current
        if current is None:
            return self._copy_channel_info(incoming)

        if current.element_type == BaseType.UNKNOWN:
            current.element_type = incoming.element_type
            current.element_exact_type = incoming.element_exact_type
        elif incoming.element_type != BaseType.UNKNOWN and current.element_type != incoming.element_type:
            merged = promote_numeric(current.element_type, incoming.element_type)
            if merged == BaseType.UNKNOWN:
                raise ZincTypeError(f"{label} have incompatible channel payload types")
            current.element_type = merged
            current.element_exact_type = self._merge_exact_type_for_base(
                current.element_exact_type,
                incoming.element_exact_type,
                merged,
                f"{label} have incompatible channel payload types",
            )
        else:
            current.element_exact_type = self._merge_exact_type_for_base(
                current.element_exact_type,
                incoming.element_exact_type,
                current.element_type,
                f"{label} have incompatible channel payload types",
            )

        if current.element_type == BaseType.TUPLE:
            current.element_tuple_info = self._merge_tuple_info(
                current.element_tuple_info,
                incoming.element_tuple_info,
            )
        if current.element_type == BaseType.CALLABLE:
            current.element_callable_info = self._merge_callable_info(
                current.element_callable_info,
                incoming.element_callable_info,
                "channel payload",
            )
        if current.element_type == BaseType.STRUCT:
            if (
                current.element_struct_qualified_name is not None
                or current.element_anonymous_struct_info is not None
            ) and not self._structs_compatible(
                current.element_struct_qualified_name,
                current.element_anonymous_struct_info,
                incoming.element_struct_qualified_name,
                incoming.element_anonymous_struct_info,
            ):
                raise ZincTypeError(f"{label} have incompatible channel payload types")
            if current.element_struct_qualified_name is None:
                current.element_struct_qualified_name = incoming.element_struct_qualified_name
            if current.element_anonymous_struct_info is None and incoming.element_anonymous_struct_info is not None:
                current.element_anonymous_struct_info = self._copy_anonymous_struct_info(
                    incoming.element_anonymous_struct_info
                )

        current.is_bounded = current.is_bounded or incoming.is_bounded
        return current

    def _merge_value_infos(
        self,
        current: ResolvedValueInfo,
        incoming: ResolvedValueInfo,
        label: str = "if-expression branches",
    ) -> ResolvedValueInfo:
        """Merge two value descriptions, treating NEVER as compatible with any normal branch."""
        if current.base_type == BaseType.NEVER:
            return incoming
        if incoming.base_type == BaseType.NEVER:
            return current
        if current.base_type == BaseType.VOID or incoming.base_type == BaseType.VOID:
            if current.base_type == incoming.base_type:
                return ResolvedValueInfo(BaseType.VOID)
            raise ZincTypeError(f"{label} have incompatible types")

        merged_type = current.base_type
        if merged_type == BaseType.UNKNOWN:
            merged_type = incoming.base_type
        elif incoming.base_type != BaseType.UNKNOWN and incoming.base_type != merged_type:
            promoted = promote_numeric(merged_type, incoming.base_type)
            if promoted == BaseType.UNKNOWN:
                raise ZincTypeError(f"{label} have incompatible types")
            merged_type = promoted

        merged = ResolvedValueInfo(
            base_type=merged_type,
            exact_type=self._merge_exact_type_for_base(
                current.exact_type,
                incoming.exact_type,
                merged_type,
                label,
            ),
        )
        if merged_type == BaseType.ARRAY:
            merged.array_info = self._merge_array_info(
                self._copy_array_info(current.array_info),
                incoming.array_info,
                label,
            )
        elif merged_type == BaseType.CHANNEL:
            merged.channel_info = self._merge_channel_info(
                self._copy_channel_info(current.channel_info),
                incoming.channel_info,
                label,
            )
        elif merged_type == BaseType.DICT:
            merged.dict_info = self._merge_dict_info(
                self._copy_dict_info(current.dict_info),
                incoming.dict_info,
            )
        elif merged_type == BaseType.SET:
            merged.set_info = self._merge_set_info(
                self._copy_set_info(current.set_info),
                incoming.set_info,
            )
        elif merged_type == BaseType.TUPLE:
            merged.tuple_info = self._merge_tuple_info(
                self._copy_tuple_info(current.tuple_info),
                incoming.tuple_info,
            )
        elif merged_type == BaseType.CALLABLE:
            merged.callable_info = self._merge_callable_info(
                self._copy_callable_info(current.callable_info),
                incoming.callable_info,
                "if-expression result",
            )
        elif merged_type == BaseType.STRUCT:
            if not self._structs_compatible(
                current.struct_qualified_name,
                current.anonymous_struct_info,
                incoming.struct_qualified_name,
                incoming.anonymous_struct_info,
            ):
                raise ZincTypeError(f"{label} have incompatible types")
            merged.struct_qualified_name = current.struct_qualified_name or incoming.struct_qualified_name
            merged.anonymous_struct_info = self._copy_anonymous_struct_info(
                current.anonymous_struct_info or incoming.anonymous_struct_info
            )
        return merged

    def _predeclare_block_lexical_functions(self, block_ctx) -> None:
        """Register nested function names before walking block contents."""
        for stmt in block_ctx.statement():
            if stmt.functionDeclaration():
                fn_ctx = stmt.functionDeclaration()
                self._register_lexical_function_stub(
                    fn_ctx.IDENTIFIER().getText(),
                    fn_ctx,
                    is_async=False,
                    display_name=fn_ctx.IDENTIFIER().getText(),
                )
            elif stmt.asyncFunctionDeclaration():
                fn_ctx = stmt.asyncFunctionDeclaration()
                self._register_lexical_function_stub(
                    fn_ctx.IDENTIFIER().getText(),
                    fn_ctx,
                    is_async=True,
                    display_name=fn_ctx.IDENTIFIER().getText(),
                )

    def _visit_tail_statement_as_value(self, stmt_ctx) -> ResolvedValueInfo:
        """Evaluate the trailing statement of a value-producing block."""
        if stmt_ctx.expressionStatement():
            return self._value_info_from_expression(
                stmt_ctx.expressionStatement().expression()
            )
        if stmt_ctx.block():
            return self._visit_block_statements(stmt_ctx.block(), as_value=True)
        if stmt_ctx.ifStatement():
            return self._analyze_if_statement_as_value(stmt_ctx.ifStatement())
        if stmt_ctx.returnStatement():
            self.visit(stmt_ctx.returnStatement())
            return ResolvedValueInfo(BaseType.NEVER)
        if stmt_ctx.breakStatement():
            self.visit(stmt_ctx.breakStatement())
            return ResolvedValueInfo(BaseType.NEVER)
        if stmt_ctx.continueStatement():
            self.visit(stmt_ctx.continueStatement())
            return ResolvedValueInfo(BaseType.NEVER)

        self.visit(stmt_ctx)
        return ResolvedValueInfo(BaseType.VOID)

    def _visit_block_statements(
        self,
        block_ctx,
        *,
        as_value: bool,
    ) -> ResolvedValueInfo | None:
        """Visit a block either as statements or as a value-producing block."""
        self._lexical_function_scopes.append({})
        try:
            self._predeclare_block_lexical_functions(block_ctx)
            statements = list(block_ctx.statement())
            if not as_value:
                for stmt in statements:
                    self.visit(stmt)
                return None
            if not statements:
                return ResolvedValueInfo(BaseType.VOID)
            for stmt in statements[:-1]:
                self.visit(stmt)
            return self._visit_tail_statement_as_value(statements[-1])
        finally:
            self._lexical_function_scopes.pop()

    def _analyze_if_expression_ctx(self, ctx) -> ResolvedValueInfo:
        """Resolve the value type of an expression-form if."""
        self._require_boolean_condition(ctx.expression(), "if condition")
        then_scope = self._next_block_name("if")
        self.symbols.enter_scope(then_scope)
        try:
            then_value = self._visit_block_statements(ctx.block(0), as_value=True)
        finally:
            self.symbols.exit_scope()

        else_value: ResolvedValueInfo | None = None
        if ctx.ELSE():
            if len(ctx.block()) > 1:
                else_scope = self._next_block_name("if")
                self.symbols.enter_scope(else_scope)
                try:
                    else_value = self._visit_block_statements(ctx.block(1), as_value=True)
                finally:
                    self.symbols.exit_scope()
            else:
                else_value = self._analyze_if_expression_ctx(ctx.ifExpression())
        else:
            if then_value.base_type not in {BaseType.VOID, BaseType.NEVER}:
                raise ZincTypeError("if-expression without else must resolve to unit or diverge")
            else_value = ResolvedValueInfo(BaseType.VOID)

        return self._merge_value_infos(then_value, else_value)

    def _analyze_if_statement_as_value(self, ctx: ZincParser.IfStatementContext) -> ResolvedValueInfo:
        """Resolve the value type of a statement-form if used in tail position."""
        if len(ctx.block()) > len(ctx.expression()):
            else_scope = self._next_block_name("if")
            self.symbols.enter_scope(else_scope)
            try:
                else_value = self._visit_block_statements(ctx.block(-1), as_value=True)
            finally:
                self.symbols.exit_scope()
        else:
            else_value = ResolvedValueInfo(BaseType.VOID)
        for index in range(len(ctx.expression()) - 1, -1, -1):
            self._require_boolean_condition(ctx.expression(index), "if condition")
            branch_scope = self._next_block_name("if")
            self.symbols.enter_scope(branch_scope)
            try:
                branch_value = self._visit_block_statements(ctx.block(index), as_value=True)
            finally:
                self.symbols.exit_scope()
            if index == len(ctx.expression()) - 1 and len(ctx.block()) == len(ctx.expression()):
                if branch_value.base_type not in {BaseType.VOID, BaseType.NEVER}:
                    raise ZincTypeError("if-expression without else must resolve to unit or diverge")
            else_value = self._merge_value_infos(branch_value, else_value)
        return else_value

    def _array_info_from_symbol(self, symbol: Symbol | None) -> ArrayTypeInfo | None:
        """Build array metadata from a symbol carrying element metadata."""
        if symbol is None or symbol.resolved_type != BaseType.ARRAY or symbol.element_type is None:
            return None
        return ArrayTypeInfo(
            element_type=symbol.element_type,
            element_exact_type=symbol.element_exact_type,
            element_tuple_info=self._copy_tuple_info(symbol.tuple_info),
            element_callable_info=self._copy_callable_info(symbol.callable_info),
            element_struct_qualified_name=symbol.element_struct_qualified_name,
            element_anonymous_struct_info=self._copy_anonymous_struct_info(symbol.element_anonymous_struct_info),
        )

    def _merge_callable_info(
        self,
        current: CallableTypeInfo | None,
        incoming: CallableTypeInfo | None,
        label: str,
    ) -> CallableTypeInfo | None:
        """Merge callable metadata, requiring compatible signatures and unioning targets."""
        if incoming is None:
            return current
        if current is None:
            return self._copy_callable_info(incoming)
        try:
            return current.merge_targets_from(incoming)
        except ValueError as exc:
            if len(current.param_types) != len(incoming.param_types):
                raise ZincTypeError(f"incompatible callable signatures for {label}") from exc
            merged = self._copy_callable_info(current) or CallableTypeInfo()
            while len(merged.param_exact_types) < len(merged.param_types):
                merged.param_exact_types.append(None)
            for i, incoming_type in enumerate(incoming.param_types):
                current_type = merged.param_types[i]
                incoming_exact = incoming.param_exact_types[i] if i < len(incoming.param_exact_types) else None
                if current_type == BaseType.UNKNOWN:
                    merged.param_types[i] = incoming_type
                    merged.param_exact_types[i] = incoming_exact
                elif incoming_type == BaseType.UNKNOWN:
                    pass
                elif current_type != incoming_type:
                    promoted = promote_numeric(current_type, incoming_type)
                    if promoted == BaseType.UNKNOWN:
                        raise ZincTypeError(f"incompatible callable signatures for {label}") from exc
                    merged.param_types[i] = promoted
                    merged.param_exact_types[i] = promote_exact_numeric(
                        merged.param_exact_types[i],
                        incoming_exact,
                        promoted,
                    )
                elif (
                    merged.param_exact_types[i] is not None
                    and incoming_exact is not None
                    and not self._exact_types_compatible(
                        current_type,
                        incoming_type,
                        expected_exact_type=merged.param_exact_types[i],
                        actual_exact_type=incoming_exact,
                    )
                ):
                    raise ZincTypeError(f"incompatible callable signatures for {label}") from exc
                elif merged.param_exact_types[i] is None:
                    merged.param_exact_types[i] = incoming_exact
                if merged.param_types[i] == BaseType.STRUCT:
                    current_named = merged.param_struct_qualified_names.get(i)
                    incoming_named = incoming.param_struct_qualified_names.get(i)
                    current_anon = merged.param_anonymous_struct_infos.get(i)
                    incoming_anon = incoming.param_anonymous_struct_infos.get(i)
                    if current_named is None and incoming_named is not None:
                        merged.param_struct_qualified_names[i] = incoming_named
                    if current_anon is None and incoming_anon is not None:
                        merged.param_anonymous_struct_infos[i] = self._copy_anonymous_struct_info(incoming_anon)
                    if not self._structs_compatible(
                        merged.param_struct_qualified_names.get(i),
                        merged.param_anonymous_struct_infos.get(i),
                        incoming_named,
                        incoming_anon,
                    ):
                        raise ZincTypeError(f"incompatible callable signatures for {label}") from exc
                merged_nested = self._merge_callable_info(
                    merged.param_callable_infos.get(i),
                    incoming.param_callable_infos.get(i),
                    label,
                )
                if merged_nested is not None:
                    merged.param_callable_infos[i] = merged_nested
            if merged.return_type == BaseType.UNKNOWN:
                merged.return_type = incoming.return_type
                merged.return_exact_type = incoming.return_exact_type
            elif incoming.return_type not in {BaseType.UNKNOWN, merged.return_type}:
                promoted = promote_numeric(merged.return_type, incoming.return_type)
                if promoted == BaseType.UNKNOWN:
                    raise ZincTypeError(f"incompatible callable signatures for {label}") from exc
                merged.return_type = promoted
                merged.return_exact_type = promote_exact_numeric(
                    merged.return_exact_type,
                    incoming.return_exact_type,
                    promoted,
                )
            elif (
                incoming.return_type != BaseType.UNKNOWN
                and merged.return_exact_type is not None
                and incoming.return_exact_type is not None
                and not self._exact_types_compatible(
                    merged.return_type,
                    incoming.return_type,
                    expected_exact_type=merged.return_exact_type,
                    actual_exact_type=incoming.return_exact_type,
                )
            ):
                raise ZincTypeError(f"incompatible callable signatures for {label}") from exc
            elif merged.return_exact_type is None:
                merged.return_exact_type = incoming.return_exact_type
            if merged.return_type == BaseType.STRUCT:
                if merged.return_struct_qualified_name is None and incoming.return_struct_qualified_name is not None:
                    merged.return_struct_qualified_name = incoming.return_struct_qualified_name
                if merged.return_anonymous_struct_info is None and incoming.return_anonymous_struct_info is not None:
                    merged.return_anonymous_struct_info = self._copy_anonymous_struct_info(
                        incoming.return_anonymous_struct_info
                    )
                if not self._structs_compatible(
                    merged.return_struct_qualified_name,
                    merged.return_anonymous_struct_info,
                    incoming.return_struct_qualified_name,
                    incoming.return_anonymous_struct_info,
                ):
                    raise ZincTypeError(f"incompatible callable signatures for {label}") from exc
            merged.return_callable_info = self._merge_callable_info(
                merged.return_callable_info,
                incoming.return_callable_info,
                label,
            )
            seen = {target.storage_key() for target in merged.targets}
            for target in incoming.targets:
                if target.storage_key() not in seen:
                    merged.targets = (*merged.targets, target)
                    seen.add(target.storage_key())
            return merged

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
        symbol.channel_info = self._copy_channel_info(info)
        return info

    def _merge_channel_value_type(
        self,
        channel_name: str,
        value_type: BaseType,
        value_exact_type: str | None = None,
        value_callable_info: CallableTypeInfo | None = None,
        value_struct_qualified_name: str | None = None,
        value_anonymous_struct_info: AnonymousStructTypeInfo | None = None,
    ) -> None:
        """Merge a sent value type into channel metadata."""
        targets = self._channel_param_all_infos.get(channel_name)
        if targets is None:
            targets = [self._channel_info_for_name(channel_name)]

        for chan_info in targets:
            if chan_info.element_type == BaseType.UNKNOWN:
                chan_info.element_type = value_type
                chan_info.element_exact_type = value_exact_type
            elif value_type != BaseType.UNKNOWN and value_type != chan_info.element_type:
                if chan_info.element_type == BaseType.CALLABLE and value_type == BaseType.CALLABLE:
                    pass
                else:
                    merged = promote_numeric(chan_info.element_type, value_type)
                    if merged == BaseType.UNKNOWN:
                        raise ZincTypeError("mixed channel value types are not supported")
                    chan_info.element_type = merged
                    chan_info.element_exact_type = self._merge_exact_type_for_base(
                        chan_info.element_exact_type,
                        value_exact_type,
                        merged,
                        "channel payloads",
                    )
            else:
                chan_info.element_exact_type = self._merge_exact_type_for_base(
                    chan_info.element_exact_type,
                    value_exact_type,
                    chan_info.element_type,
                    "channel payloads",
                )

            if chan_info.element_type == BaseType.CALLABLE:
                chan_info.element_callable_info = self._merge_callable_info(
                    chan_info.element_callable_info,
                    value_callable_info,
                    "channel payload",
                )
            if chan_info.element_type == BaseType.STRUCT:
                if (
                    chan_info.element_struct_qualified_name is not None
                    or chan_info.element_anonymous_struct_info is not None
                ) and not self._structs_compatible(
                    chan_info.element_struct_qualified_name,
                    chan_info.element_anonymous_struct_info,
                    value_struct_qualified_name,
                    value_anonymous_struct_info,
                ):
                    raise ZincTypeError("mixed channel value types are not supported")
                if chan_info.element_struct_qualified_name is None:
                    chan_info.element_struct_qualified_name = value_struct_qualified_name
                if chan_info.element_anonymous_struct_info is None and value_anonymous_struct_info is not None:
                    chan_info.element_anonymous_struct_info = self._copy_anonymous_struct_info(
                        value_anonymous_struct_info
                    )

    def _callable_is_transport_safe(
        self,
        callable_info: CallableTypeInfo | None,
        seen: set[str] | None = None,
    ) -> bool:
        """Return True when a callable graph is safe to move across spawn/channel boundaries."""
        if callable_info is None:
            return True
        active = seen or set()
        for target in callable_info.targets:
            if target.kind == "bound_method":
                return False
            if target.kind == "closure":
                if target.qualified_name in active:
                    continue
                closure_info = self.lexical_functions.get(target.qualified_name)
                if closure_info is None:
                    continue
                active.add(target.qualified_name)
                for capture in closure_info.captures:
                    if not self._callable_is_transport_safe(capture.callable_info, active):
                        return False
                active.remove(target.qualified_name)
        return True

    def _validate_channel_callable_send(self, callable_info: CallableTypeInfo | None) -> None:
        """Reject callable categories that are not transportable over channels in v1."""
        if not self._callable_is_transport_safe(callable_info):
            raise ZincTypeError("closure captures are not transport-safe for channel send")

    def _merge_key_type(self, current: BaseType, incoming: BaseType, label: str) -> BaseType:
        """Merge dict key or set element types, rejecting floats for Rust container keys."""
        if incoming == BaseType.FLOAT:
            raise ZincTypeError(f"{label} cannot be a float in v1")
        if incoming == BaseType.CALLABLE:
            raise ZincTypeError(f"{label} cannot be a callable in v1")
        if incoming == BaseType.ENUM:
            raise ZincTypeError(f"{label} cannot be an enum in v1")
        if current == BaseType.UNKNOWN:
            return incoming
        if incoming == BaseType.UNKNOWN or incoming == current:
            return current
        raise ZincTypeError(f"mixed {label} types are not supported")

    def _merge_value_type(self, current: BaseType, incoming: BaseType, label: str) -> BaseType:
        """Merge value types with int/float promotion."""
        if current == BaseType.CALLABLE or incoming == BaseType.CALLABLE:
            if current == BaseType.UNKNOWN:
                return incoming
            if incoming == BaseType.UNKNOWN or incoming == current:
                return current
            raise ZincTypeError(f"mixed {label} types are not supported")
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
        current.key_exact_type = self._merge_exact_type_for_base(
            current.key_exact_type,
            incoming.key_exact_type,
            current.key_type,
            "dict key return paths",
        )
        current.value_exact_type = self._merge_exact_type_for_base(
            current.value_exact_type,
            incoming.value_exact_type,
            current.value_type,
            "dict value return paths",
        )
        if current.key_type == BaseType.STRUCT and not self._structs_compatible(
            current.key_struct_qualified_name,
            current.key_anonymous_struct_info,
            incoming.key_struct_qualified_name,
            incoming.key_anonymous_struct_info,
        ):
            raise ZincTypeError("function return paths use incompatible dict key struct types")
        if current.value_type == BaseType.STRUCT and not self._structs_compatible(
            current.value_struct_qualified_name,
            current.value_anonymous_struct_info,
            incoming.value_struct_qualified_name,
            incoming.value_anonymous_struct_info,
        ):
            raise ZincTypeError("function return paths use incompatible dict value struct types")
        current.value_callable_info = self._merge_callable_info(
            current.value_callable_info,
            incoming.value_callable_info,
            "dict value",
        )
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
        current.element_exact_type = self._merge_exact_type_for_base(
            current.element_exact_type,
            incoming.element_exact_type,
            current.element_type,
            "set element return paths",
        )
        if current.element_type == BaseType.STRUCT and not self._structs_compatible(
            current.element_struct_qualified_name,
            current.element_anonymous_struct_info,
            incoming.element_struct_qualified_name,
            incoming.element_anonymous_struct_info,
        ):
            raise ZincTypeError("function return paths use incompatible set element struct types")
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
            if i >= len(current.element_exact_types):
                current.element_exact_types.extend([None] * (i + 1 - len(current.element_exact_types)))
            if i >= len(incoming.element_exact_types):
                incoming_exact = None
            else:
                incoming_exact = incoming.element_exact_types[i]
            if current_type == BaseType.TUPLE or incoming_type == BaseType.TUPLE:
                if current_type != BaseType.TUPLE or incoming_type != BaseType.TUPLE:
                    raise ZincTypeError("tuple return paths use incompatible element types")
                current.element_tuple_infos[i] = self._merge_tuple_info(
                    current.element_tuple_infos.get(i),
                    incoming.element_tuple_infos.get(i),
                ) or TupleTypeInfo()
                continue
            if current_type == BaseType.CALLABLE or incoming_type == BaseType.CALLABLE:
                if current_type != BaseType.CALLABLE or incoming_type != BaseType.CALLABLE:
                    raise ZincTypeError("tuple return paths use incompatible element types")
                merged_callable = self._merge_callable_info(
                    current.element_callable_infos.get(i),
                    incoming.element_callable_infos.get(i),
                    "tuple element",
                )
                if merged_callable is not None:
                    current.element_callable_infos[i] = merged_callable
                current.element_types[i] = BaseType.CALLABLE
                continue
            if current_type == BaseType.STRUCT or incoming_type == BaseType.STRUCT:
                if current_type != BaseType.STRUCT or incoming_type != BaseType.STRUCT:
                    raise ZincTypeError("tuple return paths use incompatible element types")
                if not self._structs_compatible(
                    current.element_struct_qualified_names.get(i),
                    current.element_anonymous_struct_infos.get(i),
                    incoming.element_struct_qualified_names.get(i),
                    incoming.element_anonymous_struct_infos.get(i),
                ):
                    raise ZincTypeError("tuple return paths use incompatible element types")
                current.element_types[i] = BaseType.STRUCT
                if current.element_struct_qualified_names.get(i) is None and incoming.element_struct_qualified_names.get(i) is not None:
                    current.element_struct_qualified_names[i] = incoming.element_struct_qualified_names[i]
                if current.element_anonymous_struct_infos.get(i) is None and incoming.element_anonymous_struct_infos.get(i) is not None:
                    current.element_anonymous_struct_infos[i] = self._copy_anonymous_struct_info(
                        incoming.element_anonymous_struct_infos[i]
                    ) or incoming.element_anonymous_struct_infos[i]
                continue
            merged = promote_numeric(current_type, incoming_type)
            if merged == BaseType.UNKNOWN and current_type != BaseType.UNKNOWN and incoming_type != BaseType.UNKNOWN:
                raise ZincTypeError("tuple return paths use incompatible element types")
            current.element_types[i] = merged
            current.element_exact_types[i] = self._merge_exact_type_for_base(
                current.element_exact_types[i],
                incoming_exact,
                merged,
                "tuple return paths",
            )
        return current

    def _tuple_info_from_dict_info(self, info: DictTypeInfo) -> TupleTypeInfo:
        """Build the item tuple type for dict iteration."""
        callable_infos: dict[int, CallableTypeInfo] = {}
        struct_names: dict[int, str] = {}
        anonymous_struct_infos: dict[int, AnonymousStructTypeInfo] = {}
        if info.value_callable_info is not None:
            callable_infos[1] = self._copy_callable_info(info.value_callable_info) or info.value_callable_info
        if info.key_struct_qualified_name is not None:
            struct_names[0] = info.key_struct_qualified_name
        if info.value_struct_qualified_name is not None:
            struct_names[1] = info.value_struct_qualified_name
        if info.key_anonymous_struct_info is not None:
            anonymous_struct_infos[0] = self._copy_anonymous_struct_info(info.key_anonymous_struct_info) or info.key_anonymous_struct_info
        if info.value_anonymous_struct_info is not None:
            anonymous_struct_infos[1] = self._copy_anonymous_struct_info(info.value_anonymous_struct_info) or info.value_anonymous_struct_info
        return TupleTypeInfo(
            element_types=[info.key_type, info.value_type],
            element_exact_types=[info.key_exact_type, info.value_exact_type],
            element_callable_infos=callable_infos,
            element_struct_qualified_names=struct_names,
            element_anonymous_struct_infos=anonymous_struct_infos,
        )

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

    def _expr_exact_type(self, ctx) -> str | None:
        """Return the resolved exact scalar type for an expression, if known."""
        symbol = self._expr_symbol(ctx)
        if symbol is None:
            return None
        return symbol.exact_type

    def _channel_info_for_expr(self, expr_ctx) -> ChannelTypeInfo | None:
        """Resolve channel metadata for a named or temporary channel expression."""
        info = self._channel_info_ref_for_expr(expr_ctx)
        return self._copy_channel_info(info)

    def _channel_info_ref_for_expr(self, expr_ctx) -> ChannelTypeInfo | None:
        """Resolve channel metadata for a named or temporary channel expression by reference."""
        if isinstance(expr_ctx, ZincParser.PrimaryExprContext):
            primary = expr_ctx.primaryExpression()
            if primary and primary.IDENTIFIER():
                name = primary.IDENTIFIER().getText()
                if name in self._channel_infos:
                    return self._channel_infos[name]
        expr_symbol = self._expr_symbol(expr_ctx)
        if expr_symbol and expr_symbol.channel_info:
            return expr_symbol.channel_info
        return None

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

    def _struct_qualified_name_for_symbol(self, symbol: Symbol | None) -> str | None:
        """Return the concrete struct type bound to a symbol, if known."""
        if symbol is None:
            return None
        return self._struct_symbol_bindings.get(symbol.unique_name)

    def _anonymous_struct_info_for_symbol(
        self,
        symbol: Symbol | None,
    ) -> AnonymousStructTypeInfo | None:
        """Return anonymous-struct metadata carried by a symbol, if any."""
        if symbol is None:
            return None
        return symbol.anonymous_struct_info

    def _struct_metadata_for_symbol(
        self,
        symbol: Symbol | None,
    ) -> tuple[str | None, AnonymousStructTypeInfo | None]:
        """Return named/anonymous struct identity metadata for a symbol."""
        return (
            self._struct_qualified_name_for_symbol(symbol),
            self._anonymous_struct_info_for_symbol(symbol),
        )

    def _structs_compatible(
        self,
        expected_named: str | None,
        expected_anon: AnonymousStructTypeInfo | None,
        actual_named: str | None,
        actual_anon: AnonymousStructTypeInfo | None,
    ) -> bool:
        """Return True when two struct identities are compatible."""
        if expected_anon is not None or actual_anon is not None:
            if expected_anon is None or actual_anon is None:
                return False
            if expected_anon.structural_key() != actual_anon.structural_key():
                return False
            if expected_named is not None or actual_named is not None:
                if expected_named is None or actual_named is None:
                    return False
                return expected_named == actual_named
            return True
        if expected_named is not None or actual_named is not None:
            if expected_named is None or actual_named is None:
                return False
            return expected_named == actual_named
        return True

    def _array_elements_compatible(
        self,
        expected: ArrayTypeInfo | None,
        actual: ArrayTypeInfo | None,
    ) -> bool:
        """Return True when two array element metadata records are compatible."""
        if expected is None or actual is None:
            return expected is None and actual is None
        if not self._exact_types_compatible(
            expected.element_type,
            actual.element_type,
            expected_exact_type=expected.element_exact_type,
            actual_exact_type=actual.element_exact_type,
        ):
            return False
        if expected.element_type == BaseType.STRUCT:
            return self._structs_compatible(
                expected.element_struct_qualified_name,
                expected.element_anonymous_struct_info,
                actual.element_struct_qualified_name,
                actual.element_anonymous_struct_info,
            )
        if expected.element_type == BaseType.TUPLE:
            return self._tuple_infos_compatible(expected.element_tuple_info, actual.element_tuple_info)
        if expected.element_type == BaseType.CALLABLE:
            return (
                expected.element_callable_info is None
                or actual.element_callable_info is None
                or expected.element_callable_info.structural_key()
                == actual.element_callable_info.structural_key()
            )
        return True

    def _tuple_infos_compatible(
        self,
        expected: TupleTypeInfo | None,
        actual: TupleTypeInfo | None,
    ) -> bool:
        """Return True when two tuple metadata records are structurally identical."""
        if expected is None or actual is None:
            return expected is None and actual is None
        if len(expected.element_types) != len(actual.element_types):
            return False
        for index, expected_type in enumerate(expected.element_types):
            actual_type = actual.element_types[index]
            if not self._exact_types_compatible(
                expected_type,
                actual_type,
                expected_exact_type=expected.element_exact_types[index] if index < len(expected.element_exact_types) else None,
                actual_exact_type=actual.element_exact_types[index] if index < len(actual.element_exact_types) else None,
            ):
                return False
            if expected_type == BaseType.TUPLE and not self._tuple_infos_compatible(
                expected.element_tuple_infos.get(index),
                actual.element_tuple_infos.get(index),
            ):
                return False
            if expected_type == BaseType.CALLABLE:
                expected_callable = expected.element_callable_infos.get(index)
                actual_callable = actual.element_callable_infos.get(index)
                if (
                    expected_callable is not None
                    and actual_callable is not None
                    and expected_callable.structural_key() != actual_callable.structural_key()
                ):
                    return False
            if expected_type == BaseType.STRUCT and not self._structs_compatible(
                expected.element_struct_qualified_names.get(index),
                expected.element_anonymous_struct_infos.get(index),
                actual.element_struct_qualified_names.get(index),
                actual.element_anonymous_struct_infos.get(index),
            ):
                return False
        return True

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
            expr_symbol = self._expr_symbol(ctx.expression())
            self.symbols.define(
                id=const.qualified_name,
                kind=SymbolKind.CONST,
                resolved_type=expr_type,
                interval=ctx.getSourceInterval(),
                exact_type=expr_symbol.exact_type if expr_symbol else self._resolved_exact_type(expr_type, None),
                constant_value=expr_symbol.constant_value if expr_symbol else None,
                line_num=ctx.start.line if ctx.start is not None else 0,
            )
        finally:
            self._current_module = previous_module

    def _resolve_function(self, func: FunctionInstance) -> None:
        """Resolve types within a function body for a specific specialization."""
        self._block_counters.clear()
        self._current_function = func.mangled_name
        self._current_module = func.module_id
        self._lexical_function_scopes = []
        self._current_return_type = BaseType.VOID  # Reset for this function
        self._current_return_exact_type = None
        self._current_return_dict_info = None
        self._current_return_set_info = None
        self._current_return_tuple_info = None
        self._current_return_callable_info = None
        self._current_return_struct_qualified_name = None
        self._current_return_anonymous_struct_info = None
        ctx = func.ctx

        # Use mangled name for scope so symbols are per-specialization
        self.symbols.enter_scope(func.mangled_name)

        lexical_info = self.lexical_functions.get(func.qualified_name)
        if lexical_info is not None:
            if not lexical_info.finalized:
                raise ZincTypeError(f"internal error: lexical function '{lexical_info.display_name}' was not finalized")
            for capture in lexical_info.captures:
                capture_symbol = self.symbols.define(
                    id=capture.name,
                    kind=SymbolKind.VARIABLE,
                    resolved_type=capture.resolved_type,
                    interval=ctx.getSourceInterval(),
                    exact_type=capture.exact_type,
                    declared_exact_type=capture.declared_exact_type,
                    has_declared_type=capture.has_declared_type,
                )
                capture_symbol.channel_info = self._copy_channel_info(capture.channel_info)
                capture_symbol.element_type = capture.element_type
                capture_symbol.element_exact_type = capture.element_exact_type
                capture_symbol.dict_info = self._copy_dict_info(capture.dict_info)
                capture_symbol.set_info = self._copy_set_info(capture.set_info)
                capture_symbol.tuple_info = self._copy_tuple_info(capture.tuple_info)
                capture_symbol.callable_info = self._copy_callable_info(capture.callable_info)
                capture_symbol.anonymous_struct_info = self._copy_anonymous_struct_info(
                    capture.anonymous_struct_info
                )
                capture_symbol.element_struct_qualified_name = capture.element_struct_qualified_name
                capture_symbol.element_anonymous_struct_info = self._copy_anonymous_struct_info(
                    capture.element_anonymous_struct_info
                )
                capture_symbol.is_captured_ref = True
                capture_symbol.binding_unique_name = capture.binding_unique_name
                if capture.struct_qualified_name is not None:
                    self._struct_symbol_bindings[capture_symbol.unique_name] = capture.struct_qualified_name

        # Define parameters with types from func.arg_types
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
                param_exact_type = func.arg_exact_types[i] if i < len(func.arg_exact_types) else None
                annotated_type = BaseType.UNKNOWN
                annotated_array_info = None
                annotated_dict_info = None
                annotated_set_info = None
                annotated_tuple_info = None
                annotated_callable_info = None
                annotated_struct_qualified_name = None
                annotated_anonymous_struct_info = None
                declared_exact_type = self._exact_type_name_from_type_ctx(param_ctx.type_())
                if param_ctx.type_():
                    (
                        annotated_type,
                        annotated_array_info,
                        annotated_dict_info,
                        annotated_set_info,
                        annotated_tuple_info,
                        annotated_callable_info,
                        annotated_struct_qualified_name,
                        annotated_anonymous_struct_info,
                    ) = self._type_metadata_from_type_ctx(param_ctx.type_())
                    actual_struct_qualified_name = func.arg_struct_qualified_names.get(i)
                    actual_anonymous_struct_info = func.arg_anonymous_struct_infos.get(i)
                    if not self._assignment_metadata_compatible(
                        annotated_type,
                        param_type,
                        expected_exact_type=self._exact_type_name_from_type_ctx(param_ctx.type_()),
                        actual_exact_type=param_exact_type,
                        expected_array=annotated_array_info,
                        actual_array=func.arg_array_infos.get(i),
                        expected_dict=annotated_dict_info,
                        actual_dict=func.arg_dict_infos.get(i),
                        expected_set=annotated_set_info,
                        actual_set=func.arg_set_infos.get(i),
                        expected_tuple=annotated_tuple_info,
                        actual_tuple=func.arg_tuple_infos.get(i),
                        expected_callable=annotated_callable_info,
                        actual_callable=func.arg_callable_infos.get(i),
                        expected_struct_qualified_name=annotated_struct_qualified_name,
                        actual_struct_qualified_name=actual_struct_qualified_name,
                        expected_anonymous_struct_info=annotated_anonymous_struct_info,
                        actual_anonymous_struct_info=actual_anonymous_struct_info,
                    ):
                        raise ZincTypeError(
                            f"parameter '{param_name}' expects a compatible '{param_ctx.type_().getText()}' value"
                        )
                    if declared_exact_type is not None:
                        param_exact_type = declared_exact_type
                param_symbol = self.symbols.define(
                    id=param_name,
                    kind=SymbolKind.PARAMETER,
                    resolved_type=param_type,
                    interval=param_ctx.getSourceInterval(),
                    exact_type=param_exact_type,
                    declared_exact_type=declared_exact_type,
                    has_declared_type=param_ctx.type_() is not None,
                    line_num=param_ctx.start.line if param_ctx.start is not None else 0,
                )
                # Track channel parameters for element type inference
                # Store the list of all caller channels for this parameter
                if param_type == BaseType.CHANNEL and i in func.arg_channel_infos:
                    # Use first one as primary reference, but store all for updating
                    all_chan_infos = func.arg_channel_infos[i]
                    if all_chan_infos:
                        self._channel_infos[param_name] = all_chan_infos[0]
                        param_symbol.channel_info = self._copy_channel_info(all_chan_infos[0])
                        # Store full list for updating all callers when element type is inferred
                        self._channel_param_all_infos[param_name] = all_chan_infos
                # Track array parameters for element type
                if param_type == BaseType.ARRAY and i in func.arg_array_infos:
                    param_symbol.element_type = func.arg_array_infos[i].element_type
                    param_symbol.element_exact_type = func.arg_array_infos[i].element_exact_type
                    param_symbol.tuple_info = self._copy_tuple_info(
                        func.arg_array_infos[i].element_tuple_info
                    )
                    param_symbol.element_struct_qualified_name = func.arg_array_infos[i].element_struct_qualified_name
                    param_symbol.element_anonymous_struct_info = self._copy_anonymous_struct_info(
                        func.arg_array_infos[i].element_anonymous_struct_info
                    )
                if param_type == BaseType.DICT and i in func.arg_dict_infos:
                    param_symbol.dict_info = self._copy_dict_info(func.arg_dict_infos[i])
                if param_type == BaseType.SET and i in func.arg_set_infos:
                    param_symbol.set_info = self._copy_set_info(func.arg_set_infos[i])
                if param_type == BaseType.TUPLE and i in func.arg_tuple_infos:
                    param_symbol.tuple_info = self._copy_tuple_info(func.arg_tuple_infos[i])
                if param_type == BaseType.CALLABLE and i in func.arg_callable_infos:
                    param_symbol.callable_info = self._copy_callable_info(func.arg_callable_infos[i])
                if param_type == BaseType.STRUCT:
                    if i in func.arg_struct_qualified_names:
                        self._struct_symbol_bindings[param_symbol.unique_name] = func.arg_struct_qualified_names[i]
                    if i in func.arg_anonymous_struct_infos:
                        param_symbol.anonymous_struct_info = self._copy_anonymous_struct_info(
                            func.arg_anonymous_struct_infos[i]
                        )
                if param_ctx.type_():
                    if annotated_type == BaseType.CALLABLE and annotated_callable_info is not None:
                        param_symbol.callable_info = self._merge_callable_info(
                            annotated_callable_info,
                            param_symbol.callable_info,
                            f"parameter '{param_name}'",
                        )
                    if annotated_type == BaseType.STRUCT:
                        if annotated_struct_qualified_name is not None:
                            self._struct_symbol_bindings[param_symbol.unique_name] = annotated_struct_qualified_name
                        if annotated_anonymous_struct_info is not None:
                            param_symbol.anonymous_struct_info = self._copy_anonymous_struct_info(
                                annotated_anonymous_struct_info
                            )

        # Visit function body (skip parameter list since we handled it)
        if hasattr(ctx, "block"):
            self.visit(ctx.block())

        self._validate_resolved_collections(func.mangled_name)

        # Store the inferred return type
        func.return_type = self._current_return_type
        func.return_exact_type = self._current_return_exact_type
        func.return_dict_info = self._copy_dict_info(self._current_return_dict_info)
        func.return_set_info = self._copy_set_info(self._current_return_set_info)
        func.return_tuple_info = self._copy_tuple_info(self._current_return_tuple_info)
        func.return_callable_info = self._copy_callable_info(self._current_return_callable_info)
        func.return_struct_qualified_name = self._current_return_struct_qualified_name
        func.return_anonymous_struct_info = self._copy_anonymous_struct_info(
            self._current_return_anonymous_struct_info
        )

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
            if i < len(func.arg_types) and func.arg_types[i] == BaseType.CALLABLE:
                param_symbol = self.symbols.lookup_by_id(param_name)
                if param_symbol and param_symbol.callable_info:
                    func.arg_callable_infos[i] = self._merge_callable_info(
                        func.arg_callable_infos.get(i),
                        param_symbol.callable_info,
                        f"function parameter '{param_name}'",
                    ) or CallableTypeInfo()

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

    def _sanitize_generated_name(self, text: str) -> str:
        """Convert a compiler-generated name fragment into a Rust-safe identifier."""
        cleaned = re.sub(r"[^0-9A-Za-z_]+", "_", text)
        cleaned = cleaned.strip("_")
        return cleaned or "closure"

    def _current_lexical_function(self, name: str) -> LexicalFunctionInfo | None:
        """Return the visible lexical function with this name, if any."""
        for scope in reversed(self._lexical_function_scopes):
            if name in scope:
                return scope[name]
        return None

    def _register_lexical_function_stub(
        self,
        name: str,
        ctx: ParserRuleContext,
        *,
        is_async: bool,
        display_name: str,
    ) -> LexicalFunctionInfo:
        """Create or reuse a lexical function stub visible within the current block."""
        if self._current_module is None or self._current_function is None:
            raise ZincTypeError("lexical functions require an active function context")
        if not self._lexical_function_scopes:
            raise ZincTypeError("lexical function stubs require an active lexical scope")

        current_scope = self._lexical_function_scopes[-1]
        existing = current_scope.get(name)
        if existing is not None:
            return existing

        start, stop = ctx.getSourceInterval()
        owner_fragment = self._sanitize_generated_name(self._current_function)
        name_fragment = self._sanitize_generated_name(name)
        generated_name = f"__lexical_{owner_fragment}_{name_fragment}_{start}_{stop}"
        qualified_name = self.module_graph.qualified_name(self._current_module, generated_name)
        info = LexicalFunctionInfo(
            name=name,
            qualified_name=qualified_name,
            owner_function=self._current_function,
            module_id=self._current_module,
            ctx=ctx,
            is_async=is_async,
            display_name=display_name,
        )
        current_scope[name] = info
        self.lexical_functions[qualified_name] = info
        self.atlas.function_defs[qualified_name] = ctx
        return info

    def _copy_capture_binding_info(self, symbol: Symbol) -> CaptureBindingInfo:
        """Snapshot the relevant type metadata for one captured binding."""
        return CaptureBindingInfo(
            name=symbol.id or "",
            binding_unique_name=symbol.unique_name,
            resolved_type=symbol.resolved_type,
            exact_type=symbol.exact_type,
            declared_exact_type=symbol.declared_exact_type,
            has_declared_type=symbol.has_declared_type,
            channel_info=self._copy_channel_info(symbol.channel_info),
            element_type=symbol.element_type,
            element_exact_type=symbol.element_exact_type,
            dict_info=self._copy_dict_info(symbol.dict_info),
            set_info=self._copy_set_info(symbol.set_info),
            tuple_info=self._copy_tuple_info(symbol.tuple_info),
            callable_info=self._copy_callable_info(symbol.callable_info),
            struct_qualified_name=self._struct_qualified_name_for_symbol(symbol),
            anonymous_struct_info=self._copy_anonymous_struct_info(symbol.anonymous_struct_info),
            element_struct_qualified_name=symbol.element_struct_qualified_name,
            element_anonymous_struct_info=self._copy_anonymous_struct_info(symbol.element_anonymous_struct_info),
        )

    def _analyze_lexical_captures(self, info: LexicalFunctionInfo) -> None:
        """Compute captures for a lambda or nested function using the current lexical environment."""
        if info.finalized:
            return

        ctx = info.ctx
        body_ctx = ctx.block() if hasattr(ctx, "block") else None
        if body_ctx is None:
            raise ZincTypeError("lexical functions require a block body")

        local_names: set[str] = set()
        if hasattr(ctx, "parameterList") and ctx.parameterList():
            local_names.update(
                param_ctx.IDENTIFIER().getText()
                for param_ctx in ctx.parameterList().parameter()
            )

        local_function_names: set[str] = set()

        def predeclare_nested(block_ctx) -> None:
            if block_ctx is None:
                return
            for stmt in block_ctx.statement():
                if stmt.functionDeclaration():
                    local_function_names.add(stmt.functionDeclaration().IDENTIFIER().getText())
                if stmt.asyncFunctionDeclaration():
                    local_function_names.add(stmt.asyncFunctionDeclaration().IDENTIFIER().getText())

        predeclare_nested(body_ctx)

        captures: list[CaptureBindingInfo] = []
        seen_bindings: set[str] = set()

        top_level_names: set[str] = set()
        if self._current_module is not None:
            module = self.module_graph.get_module(self._current_module)
            top_level_names.update(module.symbols.keys())
            top_level_names.update(module.injected_symbols.keys())
        top_level_names.update(
            {
                "print",
                "chan",
                "close",
                "dict",
                "sort_dict",
                "set",
                "sort_set",
                "meta",
                "type",
                "line",
                "has_component",
                "implements",
                "ComponentOrder",
                "Context",
            }
        )

        def record_capture(name: str) -> None:
            if name in local_names or name in local_function_names or name in top_level_names:
                return
            if name == "self":
                raise ZincTypeError("closures cannot capture 'self'")
            outer_symbol = self.symbols.lookup_by_id(name)
            if outer_symbol is None:
                return
            if outer_symbol.kind not in {SymbolKind.VARIABLE, SymbolKind.PARAMETER}:
                return
            if outer_symbol.unique_name.startswith(f"{self._current_function}."):
                pass
            if outer_symbol.unique_name in seen_bindings:
                return
            outer_symbol.is_captured_binding = True
            captures.append(self._copy_capture_binding_info(outer_symbol))
            seen_bindings.add(outer_symbol.unique_name)

        def walk(node) -> None:
            if node is None:
                return
            if isinstance(node, ZincParser.PrimaryExpressionContext):
                if node.IDENTIFIER():
                    record_capture(node.IDENTIFIER().getText())
                return
            if isinstance(node, ZincParser.SuperAssignmentContext):
                record_capture(node.IDENTIFIER().getText())
                walk(node.expression())
                return
            if isinstance(node, ZincParser.FunctionDeclarationContext):
                return
            if isinstance(node, ZincParser.AsyncFunctionDeclarationContext):
                return
            if isinstance(node, ZincParser.VariableAssignmentContext):
                walk(node.expression())
                target = node.assignmentTarget()
                if target.IDENTIFIER():
                    local_names.add(target.IDENTIFIER().getText())
                elif target.tupleAssignmentTarget():
                    local_names.update(
                        token.getText()
                        for token in target.tupleAssignmentTarget().getTokens(ZincParser.IDENTIFIER)
                    )
                return
            if isinstance(node, ZincParser.TypedVariableAssignmentContext):
                walk(node.expression())
                local_names.add(node.IDENTIFIER().getText())
                return
            if isinstance(node, ZincParser.ForStatementContext):
                walk(node.expression())
                binding = node.forBinding()
                if binding.IDENTIFIER():
                    local_names.add(binding.IDENTIFIER().getText())
                elif binding.tupleAssignmentTarget():
                    local_names.update(
                        token.getText()
                        for token in binding.tupleAssignmentTarget().getTokens(ZincParser.IDENTIFIER)
                    )
                walk(node.block())
                return
            if isinstance(node, ZincParser.BlockContext):
                nested_declared: list[str] = []
                for stmt in node.statement():
                    if stmt.functionDeclaration():
                        nested_declared.append(stmt.functionDeclaration().IDENTIFIER().getText())
                    if stmt.asyncFunctionDeclaration():
                        nested_declared.append(stmt.asyncFunctionDeclaration().IDENTIFIER().getText())
                previous_function_names = set(local_function_names)
                local_function_names.update(nested_declared)
                for stmt in node.statement():
                    walk(stmt)
                local_function_names.clear()
                local_function_names.update(previous_function_names)
                return
            if hasattr(node, "getChildCount"):
                for i in range(node.getChildCount()):
                    child = node.getChild(i)
                    if isinstance(child, ParserRuleContext):
                        walk(child)

        walk(body_ctx)
        info.captures = captures
        info.finalized = True

    def _callable_info_from_function_ctx(
        self,
        ctx,
        target: CallableTarget,
    ) -> CallableTypeInfo:
        """Build callable metadata from a function or lambda parse node."""
        param_types: list[BaseType] = []
        param_exact_types: list[str | None] = []
        param_array_infos: dict[int, ArrayTypeInfo] = {}
        param_dict_infos: dict[int, DictTypeInfo] = {}
        param_set_infos: dict[int, SetTypeInfo] = {}
        param_tuple_infos: dict[int, TupleTypeInfo] = {}
        param_callable_infos: dict[int, CallableTypeInfo] = {}
        param_struct_qualified_names: dict[int, str] = {}
        param_anonymous_struct_infos: dict[int, AnonymousStructTypeInfo] = {}
        if hasattr(ctx, "parameterList") and ctx.parameterList():
            for i, param_ctx in enumerate(ctx.parameterList().parameter()):
                if param_ctx.type_():
                    (
                        param_type,
                        param_array,
                        param_dict,
                        param_set,
                        param_tuple,
                        param_callable,
                        param_struct_qualified_name,
                        param_anonymous_struct_info,
                    ) = self._type_metadata_from_type_ctx(param_ctx.type_())
                else:
                    param_type = BaseType.UNKNOWN
                    param_array = None
                    param_dict = None
                    param_set = None
                    param_tuple = None
                    param_callable = None
                    param_struct_qualified_name = None
                    param_anonymous_struct_info = None
                param_types.append(param_type)
                param_exact_types.append(self._exact_type_name_from_type_ctx(param_ctx.type_()))
                if param_array is not None:
                    param_array_infos[i] = param_array
                if param_dict is not None:
                    param_dict_infos[i] = param_dict
                if param_set is not None:
                    param_set_infos[i] = param_set
                if param_tuple is not None:
                    param_tuple_infos[i] = param_tuple
                if param_callable is not None:
                    param_callable_infos[i] = param_callable
                if param_struct_qualified_name is not None:
                    param_struct_qualified_names[i] = param_struct_qualified_name
                if param_anonymous_struct_info is not None:
                    param_anonymous_struct_infos[i] = param_anonymous_struct_info
        return CallableTypeInfo(
            param_types=param_types,
            param_exact_types=param_exact_types,
            param_array_infos=param_array_infos,
            param_dict_infos=param_dict_infos,
            param_set_infos=param_set_infos,
            param_tuple_infos=param_tuple_infos,
            param_callable_infos=param_callable_infos,
            param_struct_qualified_names=param_struct_qualified_names,
            param_anonymous_struct_infos=param_anonymous_struct_infos,
            return_type=self._callable_return_hint(ctx),
            targets=(target,),
        )

    def _callable_return_hint(self, ctx) -> BaseType:
        """Return a cheap initial return-type hint for callable declarations."""
        block_ctx = ctx.block() if hasattr(ctx, "block") else None
        if block_ctx is None:
            return BaseType.UNKNOWN

        saw_value_return = False

        def walk(node) -> None:
            nonlocal saw_value_return
            if node is None or saw_value_return:
                return
            if isinstance(node, ZincParser.FunctionDeclarationContext):
                return
            if isinstance(node, ZincParser.AsyncFunctionDeclarationContext):
                return
            if isinstance(node, ZincParser.LambdaExpressionContext):
                return
            if isinstance(node, ZincParser.ReturnStatementContext):
                if node.expression() is not None:
                    saw_value_return = True
                return
            if hasattr(node, "getChildCount"):
                for i in range(node.getChildCount()):
                    child = node.getChild(i)
                    if isinstance(child, ParserRuleContext):
                        walk(child)

        walk(block_ctx)
        return BaseType.UNKNOWN if saw_value_return else BaseType.VOID

    def _callable_info_from_method(
        self,
        method: StructMethodInfo,
        target: CallableTarget,
        *,
        owner_qualified_name: str | None = None,
        owner_kind: str = "struct",
    ) -> CallableTypeInfo:
        """Build callable metadata from analyzed struct-method metadata."""
        param_types: list[BaseType] = []
        param_exact_types: list[str | None] = []
        for _name, type_ann, resolved in method.parameters:
            param_types.append(self._type_name_to_base(resolved or type_ann))
            param_exact_types.append(self._exact_type_name_from_text(resolved or type_ann))
        return_info = self._resolved_named_type_info(
            method.return_type,
            source_module_id=method.source_module_id,
            owner_qualified_name=owner_qualified_name,
            owner_kind=owner_kind,
        )
        return CallableTypeInfo(
            param_types=param_types,
            param_exact_types=param_exact_types,
            return_type=return_info.base_type,
            return_exact_type=return_info.exact_type,
            return_struct_qualified_name=return_info.struct_qualified_name,
            return_anonymous_struct_info=self._copy_anonymous_struct_info(return_info.anonymous_struct_info),
            targets=(target,),
        )

    def _context_cancel_callable_info(self) -> CallableTypeInfo:
        """Return the callable signature used by Context.with_cancel()."""
        return CallableTypeInfo(
            param_types=[],
            param_exact_types=[],
            return_type=BaseType.VOID,
            targets=(
                CallableTarget(
                    kind="context_cancel",
                    qualified_name="__zinc_context_cancel",
                    display_name="cancel",
                ),
            ),
        )

    def _callable_info_from_lexical_function(self, info: LexicalFunctionInfo) -> CallableTypeInfo:
        """Build callable metadata for a nested sync function."""
        if info.is_async:
            raise ZincTypeError("async functions cannot be used as callable values")
        target = CallableTarget(
            kind="closure",
            qualified_name=info.qualified_name,
            display_name=info.display_name,
        )
        return self._callable_info_from_function_ctx(info.ctx, target)

    def _callable_info_from_symbol_path(self, path: list[str]) -> CallableTypeInfo | None:
        """Resolve a value-position path as a callable reference, if possible."""
        if self._current_module is None:
            return None

        resolved_function = self.module_graph.resolve_function_path(self._current_module, path)
        if resolved_function is not None:
            if resolved_function.ctx.parentCtx and isinstance(
                resolved_function.ctx.parentCtx, ZincParser.StatementContext
            ) and resolved_function.ctx.parentCtx.asyncFunctionDeclaration():
                raise ZincTypeError("async functions cannot be used as callable values")
            target = CallableTarget(
                kind="function",
                qualified_name=resolved_function.qualified_name,
                display_name=".".join(path),
            )
            return self._callable_info_from_function_ctx(resolved_function.ctx, target)

        static_target = self.module_graph.resolve_static_method_target(self._current_module, path)
        if static_target is not None:
            owner_symbol, method_name = static_target
            owner_kind = owner_symbol.kind
            if owner_kind == "struct":
                owner = self.atlas.structs.get(owner_symbol.qualified_name)
            elif owner_kind == "enum":
                owner = self._analyze_enum_by_qualified_name(owner_symbol.qualified_name)
            else:
                owner = None
            if owner is None:
                return None
            method = next((candidate for candidate in owner.methods if candidate.name == method_name), None)
            if method is None:
                return None
            if not method.is_static:
                raise ZincTypeError("instance methods must be bound to a receiver before use as callable values")
            target = CallableTarget(
                kind="static_method",
                qualified_name=f"{owner_symbol.qualified_name}::{method_name}",
                display_name=".".join(path),
                receiver_struct_qualified_name=owner_symbol.qualified_name,
            )
            return self._callable_info_from_method(
                method,
                target,
                owner_qualified_name=owner_symbol.qualified_name,
                owner_kind=owner_kind,
            )

        return None

    def _callable_signature_is_concrete(self, callable_info: CallableTypeInfo | None) -> bool:
        """Return True when a callable signature is concrete enough to specialize."""
        if callable_info is None:
            return False
        if callable_info.return_type == BaseType.UNKNOWN:
            return False
        if any(base_type == BaseType.UNKNOWN for base_type in callable_info.param_types):
            return False
        return all(
            self._callable_signature_is_concrete(nested)
            for nested in callable_info.param_callable_infos.values()
        )

    def _materialize_callable_targets(self, callable_info: CallableTypeInfo | None) -> None:
        """Ensure concrete callable values have emitted function specializations."""
        if (
            callable_info is None
            or self._current_function is None
            or not self._callable_signature_is_concrete(callable_info)
        ):
            return

        for target in callable_info.targets:
            if target.kind not in {"function", "lambda", "closure"}:
                continue
            func_def = self.atlas.function_defs.get(target.qualified_name)
            if func_def is None:
                continue
            self.atlas.add_specialization(
                target.qualified_name,
                callable_info.param_types,
                callable_info.param_exact_types,
                func_def,
                self._current_function,
                arg_array_infos=callable_info.param_array_infos,
                arg_dict_infos=callable_info.param_dict_infos,
                arg_set_infos=callable_info.param_set_infos,
                arg_tuple_infos=callable_info.param_tuple_infos,
                arg_callable_infos=callable_info.param_callable_infos,
                arg_struct_qualified_names=callable_info.param_struct_qualified_names,
                arg_anonymous_struct_infos=callable_info.param_anonymous_struct_infos,
            )

    def _callable_return_info_from_function(self, func: FunctionInstance) -> CallableTypeInfo:
        """Convert a resolved function specialization into a callable signature."""
        return CallableTypeInfo(
            param_types=list(func.arg_types),
            param_exact_types=list(func.arg_exact_types),
            param_array_infos={
                index: self._copy_array_info(info)
                for index, info in func.arg_array_infos.items()
                if self._copy_array_info(info) is not None
            },
            param_dict_infos={
                index: self._copy_dict_info(info)
                for index, info in func.arg_dict_infos.items()
                if self._copy_dict_info(info) is not None
            },
            param_set_infos={
                index: self._copy_set_info(info)
                for index, info in func.arg_set_infos.items()
                if self._copy_set_info(info) is not None
            },
            param_tuple_infos={
                index: self._copy_tuple_info(info)
                for index, info in func.arg_tuple_infos.items()
                if self._copy_tuple_info(info) is not None
            },
            param_callable_infos={
                index: self._copy_callable_info(info)
                for index, info in func.arg_callable_infos.items()
                if self._copy_callable_info(info) is not None
            },
            param_struct_qualified_names=dict(func.arg_struct_qualified_names),
            param_anonymous_struct_infos={
                index: self._copy_anonymous_struct_info(info)
                for index, info in func.arg_anonymous_struct_infos.items()
                if self._copy_anonymous_struct_info(info) is not None
            },
            return_type=func.return_type,
            return_exact_type=func.return_exact_type,
            return_dict_info=self._copy_dict_info(func.return_dict_info),
            return_set_info=self._copy_set_info(func.return_set_info),
            return_tuple_info=self._copy_tuple_info(func.return_tuple_info),
            return_callable_info=self._copy_callable_info(func.return_callable_info),
            return_struct_qualified_name=func.return_struct_qualified_name,
            return_anonymous_struct_info=self._copy_anonymous_struct_info(
                func.return_anonymous_struct_info
            ),
        )

    def _refine_callable_signature(
        self,
        callable_info: CallableTypeInfo,
        arg_types: list[BaseType],
        arg_exact_types: list[str | None],
        arg_array_infos: dict[int, ArrayTypeInfo],
        arg_dict_infos: dict[int, DictTypeInfo],
        arg_set_infos: dict[int, SetTypeInfo],
        arg_tuple_infos: dict[int, TupleTypeInfo],
        arg_callable_infos: dict[int, CallableTypeInfo],
        arg_struct_qualified_names: dict[int, str],
        arg_anonymous_struct_infos: dict[int, AnonymousStructTypeInfo],
        return_type: BaseType,
        return_exact_type: str | None,
        return_dict_info: DictTypeInfo | None,
        return_set_info: SetTypeInfo | None,
        return_tuple_info: TupleTypeInfo | None,
        return_callable_info: CallableTypeInfo | None,
        return_struct_qualified_name: str | None,
        return_anonymous_struct_info: AnonymousStructTypeInfo | None,
    ) -> None:
        """Refine an abstract callable signature from an indirect call site."""
        if len(callable_info.param_types) != len(arg_types):
            raise ZincTypeError("indirect call arity mismatch")

        for i, arg_type in enumerate(arg_types):
            current = callable_info.param_types[i]
            current_exact = callable_info.param_exact_types[i] if i < len(callable_info.param_exact_types) else None
            incoming_exact = arg_exact_types[i] if i < len(arg_exact_types) else None
            if current == BaseType.UNKNOWN:
                callable_info.param_types[i] = arg_type
                while len(callable_info.param_exact_types) <= i:
                    callable_info.param_exact_types.append(None)
                callable_info.param_exact_types[i] = incoming_exact
            elif current != BaseType.UNKNOWN and current != arg_type:
                if promote_numeric(current, arg_type) == BaseType.UNKNOWN:
                    raise ZincTypeError("indirect call uses incompatible callable arguments")
                callable_info.param_types[i] = promote_numeric(current, arg_type)
                callable_info.param_exact_types[i] = promote_exact_numeric(
                    current_exact,
                    incoming_exact,
                    callable_info.param_types[i],
                )
            elif (
                current_exact is not None
                and incoming_exact is not None
                and not self._exact_types_compatible(
                    current,
                    arg_type,
                    expected_exact_type=current_exact,
                    actual_exact_type=incoming_exact,
                )
            ):
                if current not in {BaseType.INTEGER, BaseType.FLOAT} or arg_type not in {BaseType.INTEGER, BaseType.FLOAT}:
                    raise ZincTypeError("indirect call uses incompatible callable arguments")
            elif current_exact is None and i < len(callable_info.param_exact_types):
                callable_info.param_exact_types[i] = incoming_exact
            if arg_type == BaseType.ARRAY and i in arg_array_infos and i not in callable_info.param_array_infos:
                callable_info.param_array_infos[i] = self._copy_array_info(arg_array_infos[i])
            if arg_type == BaseType.DICT and i in arg_dict_infos and i not in callable_info.param_dict_infos:
                callable_info.param_dict_infos[i] = self._copy_dict_info(arg_dict_infos[i])
            if arg_type == BaseType.SET and i in arg_set_infos and i not in callable_info.param_set_infos:
                callable_info.param_set_infos[i] = self._copy_set_info(arg_set_infos[i])
            if arg_type == BaseType.TUPLE and i in arg_tuple_infos and i not in callable_info.param_tuple_infos:
                callable_info.param_tuple_infos[i] = self._copy_tuple_info(arg_tuple_infos[i])
            if arg_type == BaseType.CALLABLE and i in arg_callable_infos:
                merged_nested = self._merge_callable_info(
                    callable_info.param_callable_infos.get(i),
                    arg_callable_infos[i],
                    "callable parameter",
                )
                if merged_nested is not None:
                    callable_info.param_callable_infos[i] = merged_nested
            if arg_type == BaseType.STRUCT:
                current_named = callable_info.param_struct_qualified_names.get(i)
                current_anon = callable_info.param_anonymous_struct_infos.get(i)
                incoming_named = arg_struct_qualified_names.get(i)
                incoming_anon = arg_anonymous_struct_infos.get(i)
                if current_named is None and incoming_named is not None:
                    callable_info.param_struct_qualified_names[i] = incoming_named
                if current_anon is None and incoming_anon is not None:
                    copied_anon = self._copy_anonymous_struct_info(incoming_anon)
                    if copied_anon is not None:
                        callable_info.param_anonymous_struct_infos[i] = copied_anon
                if not self._structs_compatible(
                    callable_info.param_struct_qualified_names.get(i),
                    callable_info.param_anonymous_struct_infos.get(i),
                    incoming_named,
                    incoming_anon,
                ):
                    raise ZincTypeError("indirect call uses incompatible callable arguments")

        if callable_info.return_type == BaseType.UNKNOWN:
            callable_info.return_type = return_type
            callable_info.return_exact_type = return_exact_type
            callable_info.return_dict_info = self._copy_dict_info(return_dict_info)
            callable_info.return_set_info = self._copy_set_info(return_set_info)
            callable_info.return_tuple_info = self._copy_tuple_info(return_tuple_info)
            callable_info.return_callable_info = self._copy_callable_info(return_callable_info)
            callable_info.return_struct_qualified_name = return_struct_qualified_name
            callable_info.return_anonymous_struct_info = self._copy_anonymous_struct_info(
                return_anonymous_struct_info
            )
        elif callable_info.return_type != return_type:
            promoted = promote_numeric(callable_info.return_type, return_type)
            if promoted == BaseType.UNKNOWN:
                raise ZincTypeError("indirect call targets disagree on return type")
            callable_info.return_type = promoted
            callable_info.return_exact_type = promote_exact_numeric(
                callable_info.return_exact_type,
                return_exact_type,
                promoted,
            )
        elif (
            callable_info.return_exact_type is not None
            and return_exact_type is not None
            and not self._exact_types_compatible(
                callable_info.return_type,
                return_type,
                expected_exact_type=callable_info.return_exact_type,
                actual_exact_type=return_exact_type,
            )
        ):
            raise ZincTypeError("indirect call targets disagree on return type")
        elif callable_info.return_exact_type is None:
            callable_info.return_exact_type = return_exact_type
        elif return_type == BaseType.STRUCT and not self._structs_compatible(
            callable_info.return_struct_qualified_name,
            callable_info.return_anonymous_struct_info,
            return_struct_qualified_name,
            return_anonymous_struct_info,
        ):
            raise ZincTypeError("indirect call targets disagree on return type")

    def _validate_annotated_parameters(
        self,
        ctx: ParserRuleContext,
        arg_types: list[BaseType],
        arg_exact_types: list[str | None],
        arg_exprs: list,
        arg_array_infos: dict[int, ArrayTypeInfo],
        arg_dict_infos: dict[int, DictTypeInfo],
        arg_set_infos: dict[int, SetTypeInfo],
        arg_tuple_infos: dict[int, TupleTypeInfo],
        arg_callable_infos: dict[int, CallableTypeInfo],
        arg_struct_qualified_names: dict[int, str],
        arg_anonymous_struct_infos: dict[int, AnonymousStructTypeInfo],
    ) -> None:
        """Validate exact annotated parameters before specializing a function call."""
        if not hasattr(ctx, "parameterList") or ctx.parameterList() is None:
            return

        for i, param_ctx in enumerate(ctx.parameterList().parameter()):
            if param_ctx.type_() is None or i >= len(arg_types):
                continue
            actual_type = arg_types[i]
            if actual_type == BaseType.UNKNOWN:
                continue

            actual_expr = arg_exprs[i] if i < len(arg_exprs) else None
            actual_symbol = self._expr_symbol(actual_expr) if actual_expr is not None else None
            (
                expected_type,
                expected_array_info,
                expected_dict_info,
                expected_set_info,
                expected_tuple_info,
                expected_callable_info,
                expected_struct_qualified_name,
                expected_anonymous_struct_info,
            ) = self._type_metadata_from_type_ctx(param_ctx.type_())

            actual_struct_qualified_name, actual_anonymous_struct_info = self._struct_metadata_for_symbol(
                actual_symbol
            )
            actual_array_info = self._array_info_from_symbol(actual_symbol) or arg_array_infos.get(i)
            actual_dict_info = self._copy_dict_info(actual_symbol.dict_info) if actual_symbol else None
            if actual_dict_info is None:
                actual_dict_info = self._copy_dict_info(arg_dict_infos.get(i))
            actual_set_info = self._copy_set_info(actual_symbol.set_info) if actual_symbol else None
            if actual_set_info is None:
                actual_set_info = self._copy_set_info(arg_set_infos.get(i))
            actual_tuple_info = self._copy_tuple_info(actual_symbol.tuple_info) if actual_symbol else None
            if actual_tuple_info is None:
                actual_tuple_info = self._copy_tuple_info(arg_tuple_infos.get(i))
            actual_callable_info = self._copy_callable_info(actual_symbol.callable_info) if actual_symbol else None
            if actual_callable_info is None:
                actual_callable_info = self._copy_callable_info(arg_callable_infos.get(i))
            if actual_struct_qualified_name is None:
                actual_struct_qualified_name = arg_struct_qualified_names.get(i)
            if actual_anonymous_struct_info is None:
                actual_anonymous_struct_info = self._copy_anonymous_struct_info(
                    arg_anonymous_struct_infos.get(i)
                )

            if not self._assignment_metadata_compatible(
                expected_type,
                actual_type,
                expected_exact_type=self._exact_type_name_from_type_ctx(param_ctx.type_()),
                actual_exact_type=actual_symbol.exact_type if actual_symbol else arg_exact_types[i],
                actual_constant_value=self._literal_constant_value_for_expr(actual_expr, actual_symbol),
                expected_array=expected_array_info,
                actual_array=actual_array_info,
                expected_dict=expected_dict_info,
                actual_dict=actual_dict_info,
                expected_set=expected_set_info,
                actual_set=actual_set_info,
                expected_tuple=expected_tuple_info,
                actual_tuple=actual_tuple_info,
                expected_callable=expected_callable_info,
                actual_callable=actual_callable_info,
                expected_struct_qualified_name=expected_struct_qualified_name,
                actual_struct_qualified_name=actual_struct_qualified_name,
                expected_anonymous_struct_info=expected_anonymous_struct_info,
                actual_anonymous_struct_info=actual_anonymous_struct_info,
            ):
                raise ZincTypeError(
                    f"parameter '{param_ctx.IDENTIFIER().getText()}' expects a compatible "
                    f"'{param_ctx.type_().getText()}' value"
                )

    def visitLiteral(self, ctx: ZincParser.LiteralContext) -> BaseType:
        """Visit a literal and create a symbol for it."""
        text = ctx.getText()
        base_type = parse_literal(text)
        self.symbols.define_temp(
            resolved_type=base_type,
            interval=ctx.getSourceInterval(),
            exact_type=default_exact_type(base_type),
            kind=SymbolKind.LITERAL,
            constant_value=self._parse_constant_literal(text),
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
                    exact_type=symbol.exact_type,
                    constant_value=symbol.constant_value,
                )
                temp.element_type = symbol.element_type
                temp.element_exact_type = symbol.element_exact_type
                temp.channel_info = self._copy_channel_info(symbol.channel_info)
                temp.dict_info = self._copy_dict_info(symbol.dict_info)
                temp.set_info = self._copy_set_info(symbol.set_info)
                temp.tuple_info = self._copy_tuple_info(symbol.tuple_info)
                temp.callable_info = symbol.callable_info
                temp.anonymous_struct_info = self._copy_anonymous_struct_info(symbol.anonymous_struct_info)
                temp.element_struct_qualified_name = symbol.element_struct_qualified_name
                temp.element_anonymous_struct_info = self._copy_anonymous_struct_info(
                    symbol.element_anonymous_struct_info
                )
                temp.binding_unique_name = symbol.unique_name
                temp.is_captured_binding = symbol.is_captured_binding
                temp.is_captured_ref = symbol.is_captured_ref
                struct_qualified_name = self._struct_qualified_name_for_symbol(symbol)
                if struct_qualified_name is not None:
                    self._struct_symbol_bindings[temp.unique_name] = struct_qualified_name
                return symbol.resolved_type

            const_symbol = None
            if self._current_module is not None:
                resolved_const = self.module_graph.resolve_const_path(
                    self._current_module, [name]
                )
                if resolved_const:
                    const_symbol = self.symbols.lookup_by_id(resolved_const.qualified_name)
            if const_symbol:
                temp = self.symbols.define_temp(
                    resolved_type=const_symbol.resolved_type,
                    interval=ctx.getSourceInterval(),
                    exact_type=const_symbol.exact_type,
                    constant_value=const_symbol.constant_value,
                )
                temp.dict_info = self._copy_dict_info(const_symbol.dict_info)
                temp.set_info = self._copy_set_info(const_symbol.set_info)
                temp.tuple_info = self._copy_tuple_info(const_symbol.tuple_info)
                temp.callable_info = self._copy_callable_info(const_symbol.callable_info)
                temp.anonymous_struct_info = self._copy_anonymous_struct_info(const_symbol.anonymous_struct_info)
                if const_symbol.resolved_type == BaseType.ARRAY:
                    temp.element_type = const_symbol.element_type
                    temp.element_exact_type = const_symbol.element_exact_type
                    temp.element_struct_qualified_name = const_symbol.element_struct_qualified_name
                    temp.element_anonymous_struct_info = self._copy_anonymous_struct_info(
                        const_symbol.element_anonymous_struct_info
                    )
                struct_qualified_name = self._struct_qualified_name_for_symbol(const_symbol)
                if struct_qualified_name is not None:
                    self._struct_symbol_bindings[temp.unique_name] = struct_qualified_name
                return const_symbol.resolved_type

            lexical_function = self._current_lexical_function(name)
            if lexical_function is not None:
                is_direct_call = (
                    isinstance(ctx.parentCtx, ZincParser.PrimaryExprContext)
                    and isinstance(ctx.parentCtx.parentCtx, ZincParser.FunctionCallExprContext)
                    and ctx.parentCtx.parentCtx.expression() is ctx.parentCtx
                )
                if lexical_function.is_async:
                    if is_direct_call:
                        self.symbols.define_temp(
                            resolved_type=BaseType.UNKNOWN,
                            interval=ctx.getSourceInterval(),
                        )
                        return BaseType.UNKNOWN
                    raise ZincTypeError("async functions cannot be used as callable values")
                temp = self.symbols.define_temp(
                    resolved_type=BaseType.CALLABLE,
                    interval=ctx.getSourceInterval(),
                )
                temp.callable_info = self._callable_info_from_lexical_function(lexical_function)
                self._materialize_callable_targets(temp.callable_info)
                return BaseType.CALLABLE

            callable_info = self._callable_info_from_symbol_path([name])
            if callable_info is not None:
                temp = self.symbols.define_temp(
                    resolved_type=BaseType.CALLABLE,
                    interval=ctx.getSourceInterval(),
                )
                temp.callable_info = callable_info
                self._materialize_callable_targets(callable_info)
                return BaseType.CALLABLE

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

        if hasattr(ctx, "enumVariantConstruction") and ctx.enumVariantConstruction():
            return self.visit(ctx.enumVariantConstruction())

        if ctx.structInstantiation():
            return self.visit(ctx.structInstantiation())

        if hasattr(ctx, "anonymousStructLiteral") and ctx.anonymousStructLiteral():
            return self.visit(ctx.anonymousStructLiteral())

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

    def visitEnumVariantConstruction(self, ctx: ZincParser.EnumVariantConstructionContext) -> BaseType:
        """Visit enum payload construction."""
        if self._current_module is None:
            raise ZincTypeError("enum construction requires a module context")

        variant_target = self.module_graph.resolve_enum_variant_path(
            self._current_module,
            enum_variant_path_from_ctx(ctx),
        )
        if variant_target is None:
            resolved_struct = self.module_graph.resolve_struct_path(
                self._current_module,
                ctx.enumVariantPath().getText().split("."),
            )
            if resolved_struct is None:
                raise ZincTypeError(f"unknown enum variant '{ctx.enumVariantPath().getText()}'")
            struct_info = self.atlas.structs.get(resolved_struct.qualified_name)
            provided_exprs: dict[str, tuple[BaseType, Symbol | None, ParserRuleContext]] = {}
            for field_ctx in ctx.fieldInit():
                field_name = field_ctx.IDENTIFIER().getText()
                if field_name in provided_exprs:
                    raise ZincTypeError(f"struct literal has duplicate field '{field_name}'")
                field_type = self.visit(field_ctx.expression())
                provided_exprs[field_name] = (
                    field_type,
                    self._expr_symbol(field_ctx.expression()),
                    field_ctx.expression(),
                )
            if struct_info is not None:
                field_map = {field.name: field for field in struct_info.fields}
                for field_name, (actual_type, actual_symbol, actual_expr_ctx) in provided_exprs.items():
                    expected_field = field_map.get(field_name)
                    if expected_field is None:
                        raise ZincTypeError(f"struct '{struct_info.name}' has no field '{field_name}'")
                    actual_struct_qualified_name, actual_anonymous_struct_info = self._struct_metadata_for_symbol(actual_symbol)
                    actual_array_info = self._array_info_from_symbol(actual_symbol)
                    if not self._assignment_metadata_compatible(
                        expected_field.resolved_type,
                        actual_type,
                        expected_exact_type=expected_field.exact_type
                        or self._exact_type_name_from_text(expected_field.type_annotation),
                        actual_exact_type=actual_symbol.exact_type if actual_symbol else None,
                        actual_constant_value=self._literal_constant_value_for_expr(actual_expr_ctx, actual_symbol),
                        expected_array=expected_field.array_info,
                        actual_array=actual_array_info,
                        expected_dict=expected_field.dict_info,
                        actual_dict=self._copy_dict_info(actual_symbol.dict_info) if actual_symbol else None,
                        expected_set=expected_field.set_info,
                        actual_set=self._copy_set_info(actual_symbol.set_info) if actual_symbol else None,
                        expected_tuple=expected_field.tuple_info,
                        actual_tuple=self._copy_tuple_info(actual_symbol.tuple_info) if actual_symbol else None,
                        expected_callable=expected_field.callable_info,
                        actual_callable=self._copy_callable_info(actual_symbol.callable_info) if actual_symbol else None,
                        expected_struct_qualified_name=expected_field.struct_qualified_name,
                        actual_struct_qualified_name=actual_struct_qualified_name,
                        expected_anonymous_struct_info=expected_field.anonymous_struct_info,
                        actual_anonymous_struct_info=actual_anonymous_struct_info,
                    ):
                        raise ZincTypeError(
                            f"struct field '{struct_info.name}.{field_name}' expects a compatible "
                            f"'{expected_field.rust_type()}' value"
                        )
            temp = self.symbols.define_temp(
                resolved_type=BaseType.STRUCT,
                interval=ctx.getSourceInterval(),
            )
            self._struct_symbol_bindings[temp.unique_name] = resolved_struct.qualified_name
            return BaseType.STRUCT

        enum_symbol, variant_name = variant_target
        enum_info = self._analyze_enum_by_qualified_name(enum_symbol.qualified_name)
        variant = next((candidate for candidate in enum_info.variants if candidate.name == variant_name), None)
        if variant is None:
            raise ZincTypeError(f"enum '{enum_info.name}' has no variant '{variant_name}'")
        if variant.is_unit:
            raise ZincTypeError(f"unit variant '{enum_info.name}.{variant_name}' cannot be constructed with fields")

        provided_exprs: dict[str, tuple[BaseType, Symbol | None, ParserRuleContext]] = {}
        for field_ctx in ctx.fieldInit():
            field_name = field_ctx.IDENTIFIER().getText()
            if field_name in provided_exprs:
                raise ZincTypeError(
                    f"enum variant '{enum_info.name}.{variant_name}' has duplicate field '{field_name}'"
                )
            field_type = self.visit(field_ctx.expression())
            provided_exprs[field_name] = (
                field_type,
                self._expr_symbol(field_ctx.expression()),
                field_ctx.expression(),
            )

        field_map = {field.name: field for field in variant.fields}
        missing_fields = [field.name for field in variant.fields if field.name not in provided_exprs]
        if missing_fields:
            raise ZincTypeError(
                f"enum variant '{enum_info.name}.{variant_name}' is missing field '{missing_fields[0]}'"
            )

        for field_name, (actual_type, actual_symbol, actual_expr_ctx) in provided_exprs.items():
            expected_field = field_map.get(field_name)
            if expected_field is None:
                raise ZincTypeError(f"enum variant '{enum_info.name}.{variant_name}' has no field '{field_name}'")
            actual_struct_qualified_name, actual_anonymous_struct_info = self._struct_metadata_for_symbol(actual_symbol)
            actual_array_info = self._array_info_from_symbol(actual_symbol)
            if not self._assignment_metadata_compatible(
                expected_field.resolved_type,
                actual_type,
                expected_exact_type=expected_field.exact_type
                or self._exact_type_name_from_text(expected_field.type_annotation),
                actual_exact_type=actual_symbol.exact_type if actual_symbol else None,
                actual_constant_value=self._literal_constant_value_for_expr(actual_expr_ctx, actual_symbol),
                expected_array=expected_field.array_info,
                actual_array=actual_array_info,
                expected_dict=expected_field.dict_info,
                actual_dict=self._copy_dict_info(actual_symbol.dict_info) if actual_symbol else None,
                expected_set=expected_field.set_info,
                actual_set=self._copy_set_info(actual_symbol.set_info) if actual_symbol else None,
                expected_tuple=expected_field.tuple_info,
                actual_tuple=self._copy_tuple_info(actual_symbol.tuple_info) if actual_symbol else None,
                expected_callable=expected_field.callable_info,
                actual_callable=self._copy_callable_info(actual_symbol.callable_info) if actual_symbol else None,
                expected_struct_qualified_name=expected_field.struct_qualified_name,
                actual_struct_qualified_name=actual_struct_qualified_name,
                expected_anonymous_struct_info=expected_field.anonymous_struct_info,
                actual_anonymous_struct_info=actual_anonymous_struct_info,
            ):
                raise ZincTypeError(
                    f"enum variant field '{enum_info.name}.{variant_name}.{field_name}' expects a compatible "
                    f"'{expected_field.rust_type()}' value"
                )

        self.symbols.define_temp(
            resolved_type=BaseType.ENUM,
            interval=ctx.getSourceInterval(),
            exact_type=enum_symbol.qualified_name,
        )
        return BaseType.ENUM

    def visitLambdaExpr(self, ctx: ZincParser.LambdaExprContext) -> BaseType:
        """Visit an inline lambda expression."""
        return self.visit(ctx.lambdaExpression())

    def visitLambdaExpression(self, ctx: ZincParser.LambdaExpressionContext) -> BaseType:
        """Register a lambda as a lexical closure target."""
        if self._current_module is None or self._current_function is None:
            raise ZincTypeError("lambda expressions require a function context")
        start, stop = ctx.getSourceInterval()
        owner_fragment = self._sanitize_generated_name(self._current_function)
        generated_name = f"__lambda_{owner_fragment}_{start}_{stop}"
        qualified_name = self.module_graph.qualified_name(self._current_module, generated_name)
        info = self.lexical_functions.get(qualified_name)
        if info is None:
            info = LexicalFunctionInfo(
                name=generated_name,
                qualified_name=qualified_name,
                owner_function=self._current_function,
                module_id=self._current_module,
                ctx=ctx,
                is_async=False,
                display_name="<lambda>",
            )
            self.lexical_functions[qualified_name] = info
            self.atlas.function_defs[qualified_name] = ctx
        self._analyze_lexical_captures(info)
        callable_info = self._callable_info_from_lexical_function(info)
        temp = self.symbols.define_temp(
            resolved_type=BaseType.CALLABLE,
            interval=ctx.getSourceInterval(),
        )
        temp.callable_info = callable_info
        self._materialize_callable_targets(callable_info)
        return BaseType.CALLABLE

    def visitPrimaryExpr(self, ctx: ZincParser.PrimaryExprContext) -> BaseType:
        """Visit primary expression wrapper."""
        return self.visit(ctx.primaryExpression())

    def visitParenExpr(self, ctx: ZincParser.ParenExprContext) -> BaseType:
        """Handle parenthesized expressions."""
        inner_type = self.visit(ctx.expression())
        inner_symbol = self._expr_symbol(ctx.expression())
        temp = self.symbols.define_temp(
            resolved_type=inner_type,
            interval=ctx.getSourceInterval(),
            exact_type=inner_symbol.exact_type if inner_symbol else None,
            constant_value=inner_symbol.constant_value if inner_symbol else None,
        )
        temp.tuple_info = self._copy_tuple_info(inner_symbol.tuple_info) if inner_symbol else None
        temp.callable_info = self._copy_callable_info(inner_symbol.callable_info) if inner_symbol else None
        temp.anonymous_struct_info = self._copy_anonymous_struct_info(
            inner_symbol.anonymous_struct_info if inner_symbol else None
        )
        temp.element_exact_type = inner_symbol.element_exact_type if inner_symbol else None
        temp.element_struct_qualified_name = inner_symbol.element_struct_qualified_name if inner_symbol else None
        temp.element_anonymous_struct_info = self._copy_anonymous_struct_info(
            inner_symbol.element_anonymous_struct_info if inner_symbol else None
        )
        struct_qualified_name = self._struct_qualified_name_for_symbol(inner_symbol)
        if struct_qualified_name is not None:
            self._struct_symbol_bindings[temp.unique_name] = struct_qualified_name
        return inner_type

    def visitTupleLiteral(self, ctx: ZincParser.TupleLiteralContext) -> BaseType:
        """Visit tuple literal and infer element types."""
        element_types: list[BaseType] = []
        element_exact_types: list[str | None] = []
        element_tuple_infos: dict[int, TupleTypeInfo] = {}
        element_callable_infos: dict[int, CallableTypeInfo] = {}
        element_struct_qualified_names: dict[int, str] = {}
        element_anonymous_struct_infos: dict[int, AnonymousStructTypeInfo] = {}
        for i, expr_ctx in enumerate(ctx.expression()):
            element_type = self.visit(expr_ctx)
            element_types.append(element_type)
            expr_symbol = self._expr_symbol(expr_ctx)
            element_exact_types.append(expr_symbol.exact_type if expr_symbol else None)
            if element_type == BaseType.TUPLE and expr_symbol and expr_symbol.tuple_info:
                copied = self._copy_tuple_info(expr_symbol.tuple_info)
                if copied:
                    element_tuple_infos[i] = copied
            if element_type == BaseType.CALLABLE and expr_symbol and expr_symbol.callable_info:
                copied_callable = self._copy_callable_info(expr_symbol.callable_info)
                if copied_callable:
                    element_callable_infos[i] = copied_callable
            if element_type == BaseType.STRUCT and expr_symbol:
                struct_qualified_name = self._struct_qualified_name_for_symbol(expr_symbol)
                if struct_qualified_name is not None:
                    element_struct_qualified_names[i] = struct_qualified_name
                anonymous_struct_info = self._copy_anonymous_struct_info(expr_symbol.anonymous_struct_info)
                if anonymous_struct_info is not None:
                    element_anonymous_struct_infos[i] = anonymous_struct_info

        symbol = self.symbols.define_temp(
            resolved_type=BaseType.TUPLE,
            interval=ctx.getSourceInterval(),
        )
        symbol.tuple_info = TupleTypeInfo(
            element_types=element_types,
            element_exact_types=element_exact_types,
            element_tuple_infos=element_tuple_infos,
            element_callable_infos=element_callable_infos,
            element_struct_qualified_names=element_struct_qualified_names,
            element_anonymous_struct_infos=element_anonymous_struct_infos,
        )
        return BaseType.TUPLE

    def visitAdditiveExpr(self, ctx: ZincParser.AdditiveExprContext) -> BaseType:
        """Handle addition and subtraction."""
        left_type = self.visit(ctx.expression(0))
        right_type = self.visit(ctx.expression(1))
        result_type = TypeInfo.promote(TypeInfo(left_type), TypeInfo(right_type)).base
        left_symbol = self._expr_symbol(ctx.expression(0))
        right_symbol = self._expr_symbol(ctx.expression(1))
        constant_value = None
        if left_symbol and right_symbol and left_symbol.constant_value is not None and right_symbol.constant_value is not None:
            op = ctx.getChild(1).getText()
            if op == "+":
                constant_value = left_symbol.constant_value + right_symbol.constant_value
            elif op == "-":
                constant_value = left_symbol.constant_value - right_symbol.constant_value
        self.symbols.define_temp(
            resolved_type=result_type,
            interval=ctx.getSourceInterval(),
            exact_type=promote_exact_numeric(
                left_symbol.exact_type if left_symbol else None,
                right_symbol.exact_type if right_symbol else None,
                result_type,
            ),
            constant_value=constant_value,
        )
        return result_type

    def visitMultiplicativeExpr(self, ctx: ZincParser.MultiplicativeExprContext) -> BaseType:
        """Handle multiplication, division, modulo."""
        left_type = self.visit(ctx.expression(0))
        right_type = self.visit(ctx.expression(1))
        result_type = TypeInfo.promote(TypeInfo(left_type), TypeInfo(right_type)).base
        left_symbol = self._expr_symbol(ctx.expression(0))
        right_symbol = self._expr_symbol(ctx.expression(1))
        constant_value = None
        if left_symbol and right_symbol and left_symbol.constant_value is not None and right_symbol.constant_value is not None:
            op = ctx.getChild(1).getText()
            if op == "*":
                constant_value = left_symbol.constant_value * right_symbol.constant_value
            elif op == "/":
                constant_value = left_symbol.constant_value / right_symbol.constant_value
            elif op == "%":
                constant_value = left_symbol.constant_value % right_symbol.constant_value
        self.symbols.define_temp(
            resolved_type=result_type,
            interval=ctx.getSourceInterval(),
            exact_type=promote_exact_numeric(
                left_symbol.exact_type if left_symbol else None,
                right_symbol.exact_type if right_symbol else None,
                result_type,
            ),
            constant_value=constant_value,
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

        operand_symbol = self._expr_symbol(ctx.expression())
        constant_value = None
        if operand_symbol and operand_symbol.constant_value is not None:
            if operator == "-":
                constant_value = -operand_symbol.constant_value
            elif operator in {"!", "not"}:
                constant_value = not operand_symbol.constant_value

        self.symbols.define_temp(
            resolved_type=result_type,
            interval=ctx.getSourceInterval(),
            exact_type=operand_symbol.exact_type if operand_symbol else default_exact_type(result_type),
            constant_value=constant_value,
        )
        return result_type

    def visitRelationalExpr(self, ctx: ZincParser.RelationalExprContext) -> BaseType:
        """Handle relational comparisons."""
        self.visit(ctx.expression(0))
        self.visit(ctx.expression(1))
        left_symbol = self._expr_symbol(ctx.expression(0))
        right_symbol = self._expr_symbol(ctx.expression(1))
        constant_value = None
        if (
            left_symbol
            and right_symbol
            and left_symbol.constant_value is not None
            and right_symbol.constant_value is not None
        ):
            op = ctx.getChild(1).getText()
            if op == "<":
                constant_value = left_symbol.constant_value < right_symbol.constant_value
            elif op == "<=":
                constant_value = left_symbol.constant_value <= right_symbol.constant_value
            elif op == ">":
                constant_value = left_symbol.constant_value > right_symbol.constant_value
            elif op == ">=":
                constant_value = left_symbol.constant_value >= right_symbol.constant_value
        self.symbols.define_temp(
            resolved_type=BaseType.BOOLEAN,
            interval=ctx.getSourceInterval(),
            exact_type="bool",
            constant_value=constant_value,
        )
        return BaseType.BOOLEAN

    def visitEqualityExpr(self, ctx: ZincParser.EqualityExprContext) -> BaseType:
        """Handle equality comparisons."""
        self.visit(ctx.expression(0))
        self.visit(ctx.expression(1))
        left_symbol = self._expr_symbol(ctx.expression(0))
        right_symbol = self._expr_symbol(ctx.expression(1))
        constant_value = None
        if (
            left_symbol
            and right_symbol
            and left_symbol.constant_value is not None
            and right_symbol.constant_value is not None
        ):
            op = ctx.getChild(1).getText()
            if op == "==":
                constant_value = left_symbol.constant_value == right_symbol.constant_value
            else:
                constant_value = left_symbol.constant_value != right_symbol.constant_value
        self.symbols.define_temp(
            resolved_type=BaseType.BOOLEAN,
            interval=ctx.getSourceInterval(),
            exact_type="bool",
            constant_value=constant_value,
        )
        return BaseType.BOOLEAN

    def visitMembershipExpr(self, ctx: ZincParser.MembershipExprContext) -> BaseType:
        """Handle membership expressions like `x in [a, b]`."""
        self.visit(ctx.expression(0))
        self.visit(ctx.expression(1))
        left_symbol = self._expr_symbol(ctx.expression(0))
        right_symbol = self._expr_symbol(ctx.expression(1))
        constant_value = None
        if (
            left_symbol
            and right_symbol
            and left_symbol.constant_value is not None
            and right_symbol.constant_value is not None
        ):
            haystack = right_symbol.constant_value
            needle = left_symbol.constant_value
            if isinstance(haystack, MetaListValue):
                constant_value = needle in haystack.items
            elif isinstance(haystack, list):
                constant_value = needle in haystack
            elif isinstance(haystack, set):
                constant_value = needle in haystack
            elif isinstance(haystack, dict):
                constant_value = needle in haystack
        self.symbols.define_temp(
            resolved_type=BaseType.BOOLEAN,
            interval=ctx.getSourceInterval(),
            exact_type="bool",
            constant_value=constant_value,
        )
        return BaseType.BOOLEAN

    def visitLogicalAndExpr(self, ctx: ZincParser.LogicalAndExprContext) -> BaseType:
        """Handle logical AND."""
        self.visit(ctx.expression(0))
        self.visit(ctx.expression(1))
        left_symbol = self._expr_symbol(ctx.expression(0))
        right_symbol = self._expr_symbol(ctx.expression(1))
        constant_value = None
        if (
            left_symbol
            and right_symbol
            and left_symbol.constant_value is not None
            and right_symbol.constant_value is not None
        ):
            constant_value = bool(left_symbol.constant_value and right_symbol.constant_value)
        self.symbols.define_temp(
            resolved_type=BaseType.BOOLEAN,
            interval=ctx.getSourceInterval(),
            exact_type="bool",
            constant_value=constant_value,
        )
        return BaseType.BOOLEAN

    def visitLogicalOrExpr(self, ctx: ZincParser.LogicalOrExprContext) -> BaseType:
        """Handle logical OR."""
        self.visit(ctx.expression(0))
        self.visit(ctx.expression(1))
        left_symbol = self._expr_symbol(ctx.expression(0))
        right_symbol = self._expr_symbol(ctx.expression(1))
        constant_value = None
        if (
            left_symbol
            and right_symbol
            and left_symbol.constant_value is not None
            and right_symbol.constant_value is not None
        ):
            constant_value = bool(left_symbol.constant_value or right_symbol.constant_value)
        self.symbols.define_temp(
            resolved_type=BaseType.BOOLEAN,
            interval=ctx.getSourceInterval(),
            exact_type="bool",
            constant_value=constant_value,
        )
        return BaseType.BOOLEAN

    def visitArrayLiteral(self, ctx: ZincParser.ArrayLiteralContext) -> BaseType:
        """Visit array literal and infer element type from first element."""
        element_type = None
        element_exact_type = None
        element_tuple_info = None
        element_callable_info = None
        element_struct_qualified_name = None
        element_anonymous_struct_info = None
        constant_items: list[object] = []
        all_constant = True
        for expr_ctx in ctx.expression():
            expr_type = self.visit(expr_ctx)
            expr_symbol = self._expr_symbol(expr_ctx)
            if expr_symbol is None or expr_symbol.constant_value is None:
                all_constant = False
            else:
                constant_items.append(expr_symbol.constant_value)
            if element_type is None:
                element_type = expr_type
                element_exact_type = expr_symbol.exact_type if expr_symbol else None
                if expr_type == BaseType.TUPLE and expr_symbol and expr_symbol.tuple_info:
                    element_tuple_info = self._copy_tuple_info(expr_symbol.tuple_info)
                if expr_type == BaseType.CALLABLE and expr_symbol and expr_symbol.callable_info:
                    element_callable_info = self._copy_callable_info(expr_symbol.callable_info)
                if expr_type == BaseType.STRUCT and expr_symbol:
                    element_struct_qualified_name = self._struct_qualified_name_for_symbol(expr_symbol)
                    element_anonymous_struct_info = self._copy_anonymous_struct_info(
                        expr_symbol.anonymous_struct_info
                    )
            else:
                element_type = self._merge_value_type(element_type, expr_type, "array element")
                element_exact_type = self._merge_exact_type_for_base(
                    element_exact_type,
                    expr_symbol.exact_type if expr_symbol else None,
                    element_type,
                    "array element",
                )
        symbol = self.symbols.define_temp(
            resolved_type=BaseType.ARRAY,
            interval=ctx.getSourceInterval(),
            constant_value=constant_items if all_constant else None,
        )
        # Track element type from the first element
        if element_type is not None:
            symbol.element_type = element_type
            symbol.element_exact_type = element_exact_type
            symbol.tuple_info = element_tuple_info
            symbol.callable_info = element_callable_info
            symbol.element_struct_qualified_name = element_struct_qualified_name
            symbol.element_anonymous_struct_info = element_anonymous_struct_info
        return BaseType.ARRAY

    def visitCollectionLiteral(self, ctx: ZincParser.CollectionLiteralContext) -> BaseType:
        """Visit dict/set literal and infer inner types."""
        if not ctx.dictEntry() and not ctx.expression():
            raise ZincTypeError("empty collection literal {} is ambiguous; use dict(), set(), sort_dict(), or sort_set()")

        if ctx.dictEntry():
            key_type = BaseType.UNKNOWN
            value_type = BaseType.UNKNOWN
            key_exact_type = None
            value_exact_type = None
            value_callable_info = None
            key_struct_qualified_name = None
            value_struct_qualified_name = None
            key_anonymous_struct_info = None
            value_anonymous_struct_info = None
            for entry_ctx in ctx.dictEntry():
                entry_key_type = self.visit(entry_ctx.expression(0))
                entry_value_type = self.visit(entry_ctx.expression(1))
                key_type = self._merge_key_type(key_type, entry_key_type, "dict key")
                value_type = self._merge_value_type(value_type, entry_value_type, "dict value")
                key_symbol = self._expr_symbol(entry_ctx.expression(0))
                value_symbol = self._expr_symbol(entry_ctx.expression(1))
                key_exact_type = self._merge_exact_type_for_base(
                    key_exact_type,
                    key_symbol.exact_type if key_symbol else None,
                    key_type,
                    "dict key",
                )
                value_exact_type = self._merge_exact_type_for_base(
                    value_exact_type,
                    value_symbol.exact_type if value_symbol else None,
                    value_type,
                    "dict value",
                )
                if entry_key_type == BaseType.CALLABLE:
                    raise ZincTypeError("callables cannot be used as dict keys")
                if entry_value_type == BaseType.CALLABLE:
                    value_callable_info = self._merge_callable_info(
                        value_callable_info,
                        value_symbol.callable_info if value_symbol else None,
                        "dict value",
                    )
                if entry_key_type == BaseType.STRUCT and key_symbol:
                    key_struct_qualified_name = self._struct_qualified_name_for_symbol(key_symbol)
                    key_anonymous_struct_info = self._copy_anonymous_struct_info(
                        key_symbol.anonymous_struct_info
                    )
                if entry_value_type == BaseType.STRUCT and value_symbol:
                    value_struct_qualified_name = self._struct_qualified_name_for_symbol(value_symbol)
                    value_anonymous_struct_info = self._copy_anonymous_struct_info(
                        value_symbol.anonymous_struct_info
                    )

            symbol = self.symbols.define_temp(
                resolved_type=BaseType.DICT,
                interval=ctx.getSourceInterval(),
            )
            symbol.dict_info = DictTypeInfo(
                key_type=key_type,
                value_type=value_type,
                key_exact_type=key_exact_type,
                value_exact_type=value_exact_type,
                value_callable_info=value_callable_info,
                key_struct_qualified_name=key_struct_qualified_name,
                value_struct_qualified_name=value_struct_qualified_name,
                key_anonymous_struct_info=key_anonymous_struct_info,
                value_anonymous_struct_info=value_anonymous_struct_info,
                kind="dict",
            )
            return BaseType.DICT

        element_type = BaseType.UNKNOWN
        element_exact_type = None
        element_struct_qualified_name = None
        element_anonymous_struct_info = None
        for expr_ctx in ctx.expression():
            expr_type = self.visit(expr_ctx)
            element_type = self._merge_key_type(element_type, expr_type, "set element")
            expr_symbol = self._expr_symbol(expr_ctx)
            element_exact_type = self._merge_exact_type_for_base(
                element_exact_type,
                expr_symbol.exact_type if expr_symbol else None,
                element_type,
                "set element",
            )
            if expr_type == BaseType.CALLABLE:
                raise ZincTypeError("callables cannot be used as set elements")
            if expr_type == BaseType.STRUCT:
                if expr_symbol:
                    element_struct_qualified_name = self._struct_qualified_name_for_symbol(expr_symbol)
                    element_anonymous_struct_info = self._copy_anonymous_struct_info(
                        expr_symbol.anonymous_struct_info
                    )

        symbol = self.symbols.define_temp(
            resolved_type=BaseType.SET,
            interval=ctx.getSourceInterval(),
        )
        symbol.set_info = SetTypeInfo(
            element_type=element_type,
            element_exact_type=element_exact_type,
            element_struct_qualified_name=element_struct_qualified_name,
            element_anonymous_struct_info=element_anonymous_struct_info,
            kind="set",
        )
        return BaseType.SET

    def visitIndexAccessExpr(self, ctx: ZincParser.IndexAccessExprContext) -> BaseType:
        """Visit index access and return element type if array."""
        arr_type = self.visit(ctx.expression(0))
        self.visit(ctx.expression(1))
        collection_symbol = self._expr_symbol(ctx.expression(0))
        index_symbol = self._expr_symbol(ctx.expression(1))

        # Try to get element type from the array
        element_type = BaseType.UNKNOWN
        element_exact_type = None
        tuple_info = None
        callable_info = None
        struct_qualified_name = None
        anonymous_struct_info = None
        if arr_type == BaseType.ARRAY:
            arr_symbol = collection_symbol
            if arr_symbol and arr_symbol.element_type:
                element_type = arr_symbol.element_type
                element_exact_type = arr_symbol.element_exact_type
                if element_type == BaseType.TUPLE:
                    tuple_info = self._copy_tuple_info(arr_symbol.tuple_info)
                if element_type == BaseType.CALLABLE:
                    callable_info = arr_symbol.callable_info
                if element_type == BaseType.STRUCT:
                    struct_qualified_name = arr_symbol.element_struct_qualified_name
                    anonymous_struct_info = self._copy_anonymous_struct_info(
                        arr_symbol.element_anonymous_struct_info
                    )
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
                        element_exact_type = dict_symbol.dict_info.value_exact_type
                        callable_info = dict_symbol.dict_info.value_callable_info
                        struct_qualified_name = dict_symbol.dict_info.value_struct_qualified_name
                        anonymous_struct_info = self._copy_anonymous_struct_info(
                            dict_symbol.dict_info.value_anonymous_struct_info
                        )
            else:
                dict_symbol = self.symbols.lookup_by_interval(
                    dict_ctx.getSourceInterval(), self._current_function
                )
                if dict_symbol and dict_symbol.dict_info:
                    element_type = dict_symbol.dict_info.value_type
                    element_exact_type = dict_symbol.dict_info.value_exact_type
                    callable_info = dict_symbol.dict_info.value_callable_info
                    struct_qualified_name = dict_symbol.dict_info.value_struct_qualified_name
                    anonymous_struct_info = self._copy_anonymous_struct_info(
                        dict_symbol.dict_info.value_anonymous_struct_info
                    )
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
                exact_type=tuple_info.element_exact_types[index]
                if tuple_info and index < len(tuple_info.element_exact_types)
                else None,
            )
            symbol.tuple_info = self._copy_tuple_info(tuple_info.element_tuple_infos.get(index))
            symbol.callable_info = tuple_info.element_callable_infos.get(index)
            if element_type == BaseType.STRUCT:
                named_struct = tuple_info.element_struct_qualified_names.get(index)
                if named_struct is not None:
                    self._struct_symbol_bindings[symbol.unique_name] = named_struct
                symbol.anonymous_struct_info = self._copy_anonymous_struct_info(
                    tuple_info.element_anonymous_struct_infos.get(index)
                )
            return element_type

        temp = self.symbols.define_temp(
            resolved_type=element_type,
            interval=ctx.getSourceInterval(),
            exact_type=element_exact_type,
            constant_value=None,
        )
        temp.tuple_info = tuple_info if element_type == BaseType.TUPLE else None
        temp.callable_info = callable_info if element_type == BaseType.CALLABLE else None
        if element_type == BaseType.STRUCT:
            if struct_qualified_name is not None:
                self._struct_symbol_bindings[temp.unique_name] = struct_qualified_name
            temp.anonymous_struct_info = anonymous_struct_info
        if (
            collection_symbol
            and isinstance(collection_symbol.constant_value, MetaListValue)
            and index_symbol
            and isinstance(index_symbol.constant_value, int)
        ):
            index = index_symbol.constant_value
            if 0 <= index < len(collection_symbol.constant_value.items):
                temp.constant_value = collection_symbol.constant_value.items[index]
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
        receiver_type = self.visit(ctx.expression())
        receiver_symbol = self._expr_symbol(ctx.expression())
        member_name = ctx.IDENTIFIER().getText()

        if (
            receiver_symbol
            and isinstance(receiver_symbol.constant_value, MetaValue)
            and receiver_symbol.constant_value.struct_qualified_name == COMPONENT_ORDER_QNAME
        ):
            self.symbols.define_temp(
                resolved_type=BaseType.UNKNOWN,
                interval=ctx.getSourceInterval(),
            )
            return BaseType.UNKNOWN

        if receiver_symbol and isinstance(receiver_symbol.constant_value, MetaValue):
            meta_value = receiver_symbol.constant_value
            if meta_value.has_field(member_name):
                value = meta_value.get_field(member_name)
                symbol = self._record_constant_value(
                    ctx.getSourceInterval(),
                    value,
                    line_num=receiver_symbol.line_num,
                )
                return symbol.resolved_type
            if meta_value.has_method(member_name):
                temp = self.symbols.define_temp(
                    resolved_type=BaseType.CALLABLE,
                    interval=ctx.getSourceInterval(),
                    constant_value=("__meta_method__", meta_value, member_name),
                )
                return temp.resolved_type

        if self._current_module is not None:
            path = extract_identifier_path(ctx)
            if path:
                if path[0] == "ComponentOrder" and len(path) == 2 and path[1] in COMPONENT_ORDER_VARIANTS:
                    symbol = self._record_constant_value(
                        ctx.getSourceInterval(),
                        component_order_value(path[1]),
                        line_num=ctx.start.line if ctx.start is not None else 0,
                    )
                    return symbol.resolved_type
                const_symbol = self.module_graph.resolve_const_path(self._current_module, path)
                if const_symbol:
                    resolved = self.symbols.lookup_by_id(const_symbol.qualified_name)
                    if resolved:
                        self.symbols.define_temp(
                            resolved_type=resolved.resolved_type,
                            interval=ctx.getSourceInterval(),
                        )
                        return resolved.resolved_type
                static_target = self.module_graph.resolve_static_method_target(self._current_module, path)
                if static_target:
                    owner_symbol, method_name = static_target
                    if owner_symbol.kind == "struct":
                        owner = self.atlas.structs.get(owner_symbol.qualified_name)
                    elif owner_symbol.kind == "enum":
                        owner = self._analyze_enum_by_qualified_name(owner_symbol.qualified_name)
                    else:
                        owner = None
                    if owner is not None:
                        method = next((candidate for candidate in owner.methods if candidate.name == method_name), None)
                        if method is not None:
                            if not method.is_static:
                                raise ZincTypeError(
                                    "instance methods must be bound to a receiver before use as callable values"
                                )
                            temp = self.symbols.define_temp(
                                resolved_type=BaseType.CALLABLE,
                                interval=ctx.getSourceInterval(),
                            )
                            temp.callable_info = self._callable_info_from_method(
                                method,
                                CallableTarget(
                                    kind="static_method",
                                    qualified_name=f"{owner_symbol.qualified_name}::{method_name}",
                                    display_name=".".join(path),
                                    receiver_struct_qualified_name=owner_symbol.qualified_name,
                                ),
                                owner_qualified_name=owner_symbol.qualified_name,
                                owner_kind=owner_symbol.kind,
                            )
                            return BaseType.CALLABLE
                enum_variant = self.module_graph.resolve_enum_variant_path(self._current_module, path)
                if enum_variant:
                    enum_symbol, variant_name = enum_variant
                    enum_info = self._analyze_enum_by_qualified_name(enum_symbol.qualified_name)
                    variant = next((candidate for candidate in enum_info.variants if candidate.name == variant_name), None)
                    if variant is None:
                        raise ZincTypeError(f"enum '{enum_info.name}' has no variant '{variant_name}'")
                    if not variant.is_unit:
                        raise ZincTypeError(
                            f"payload variant '{enum_info.name}.{variant_name}' requires field construction"
                        )
                    self.symbols.define_temp(
                        resolved_type=BaseType.ENUM,
                        interval=ctx.getSourceInterval(),
                        exact_type=enum_symbol.qualified_name,
                    )
                    return BaseType.ENUM
                callable_info = self._callable_info_from_symbol_path(path)
                if callable_info is not None:
                    temp = self.symbols.define_temp(
                        resolved_type=BaseType.CALLABLE,
                        interval=ctx.getSourceInterval(),
                    )
                    temp.callable_info = callable_info
                    return BaseType.CALLABLE

        if receiver_type == BaseType.STRUCT:
            struct_qualified_name = self._struct_qualified_name_for_symbol(receiver_symbol)
            if struct_qualified_name:
                struct = self.atlas.structs.get(struct_qualified_name)
                if struct:
                    field = next((candidate for candidate in struct.fields if candidate.name == member_name), None)
                    if field is not None:
                        concrete_field = None
                        anonymous_struct_info = self._anonymous_struct_info_for_symbol(receiver_symbol)
                        if anonymous_struct_info is not None:
                            concrete_field = anonymous_struct_info.get_field(member_name)
                        resolved_field_type = concrete_field.resolved_type if concrete_field is not None and field.is_infer else field.resolved_type
                        resolved_exact_type = concrete_field.exact_type if concrete_field is not None and field.is_infer else None
                        resolved_dict_info = concrete_field.dict_info if concrete_field is not None and field.is_infer else field.dict_info
                        resolved_set_info = concrete_field.set_info if concrete_field is not None and field.is_infer else field.set_info
                        resolved_tuple_info = concrete_field.tuple_info if concrete_field is not None and field.is_infer else field.tuple_info
                        resolved_callable_info = concrete_field.callable_info if concrete_field is not None and field.is_infer else field.callable_info
                        resolved_anonymous_struct_info = concrete_field.anonymous_struct_info if concrete_field is not None and field.is_infer else field.anonymous_struct_info
                        resolved_struct_qname = concrete_field.struct_qualified_name if concrete_field is not None and field.is_infer else field.struct_qualified_name
                        resolved_array_info = concrete_field.array_info if concrete_field is not None and field.is_infer else field.array_info
                        temp = self.symbols.define_temp(
                            resolved_type=resolved_field_type,
                            interval=ctx.getSourceInterval(),
                            exact_type=resolved_exact_type,
                        )
                        if resolved_array_info is not None:
                            temp.element_type = resolved_array_info.element_type
                            temp.tuple_info = self._copy_tuple_info(resolved_array_info.element_tuple_info)
                            temp.callable_info = self._copy_callable_info(resolved_array_info.element_callable_info)
                            temp.element_struct_qualified_name = resolved_array_info.element_struct_qualified_name
                            temp.element_anonymous_struct_info = self._copy_anonymous_struct_info(
                                resolved_array_info.element_anonymous_struct_info
                            )
                        temp.dict_info = self._copy_dict_info(resolved_dict_info)
                        temp.set_info = self._copy_set_info(resolved_set_info)
                        temp.tuple_info = self._copy_tuple_info(resolved_tuple_info) or temp.tuple_info
                        temp.callable_info = self._copy_callable_info(resolved_callable_info)
                        temp.anonymous_struct_info = self._copy_anonymous_struct_info(resolved_anonymous_struct_info)
                        if resolved_struct_qname is not None:
                            self._struct_symbol_bindings[temp.unique_name] = resolved_struct_qname
                        return resolved_field_type
                    method = next((candidate for candidate in struct.methods if candidate.name == member_name), None)
                    receiver_name = None
                    if isinstance(ctx.expression(), ZincParser.PrimaryExprContext):
                        primary = ctx.expression().primaryExpression()
                        if primary and primary.IDENTIFIER():
                            receiver_name = primary.IDENTIFIER().getText()
                    if method is not None and receiver_name:
                        target = CallableTarget(
                            kind="bound_method",
                            qualified_name=f"{struct_qualified_name}::{member_name}",
                            display_name=f"{receiver_name}.{member_name}",
                            receiver_name=receiver_name,
                            receiver_struct_qualified_name=struct_qualified_name,
                            receiver_mutability=method.self_mutability,
                        )
                        temp = self.symbols.define_temp(
                            resolved_type=BaseType.CALLABLE,
                            interval=ctx.getSourceInterval(),
                        )
                        temp.callable_info = self._callable_info_from_method(
                            method,
                            target,
                            owner_qualified_name=struct_qualified_name,
                            owner_kind="struct",
                        )
                        return BaseType.CALLABLE
            anonymous_struct_info = self._anonymous_struct_info_for_symbol(receiver_symbol)
            if anonymous_struct_info is not None:
                field = anonymous_struct_info.get_field(member_name)
                if field is not None:
                    temp = self.symbols.define_temp(
                        resolved_type=field.resolved_type,
                        interval=ctx.getSourceInterval(),
                    )
                    temp.dict_info = self._copy_dict_info(field.dict_info)
                    temp.set_info = self._copy_set_info(field.set_info)
                    temp.tuple_info = self._copy_tuple_info(field.tuple_info)
                    temp.callable_info = self._copy_callable_info(field.callable_info)
                    temp.anonymous_struct_info = self._copy_anonymous_struct_info(field.anonymous_struct_info)
                    if field.struct_qualified_name is not None:
                        self._struct_symbol_bindings[temp.unique_name] = field.struct_qualified_name
                    if field.array_info is not None:
                        temp.element_type = field.array_info.element_type
                        temp.tuple_info = self._copy_tuple_info(field.array_info.element_tuple_info)
                        temp.callable_info = self._copy_callable_info(field.array_info.element_callable_info)
                        temp.element_struct_qualified_name = field.array_info.element_struct_qualified_name
                        temp.element_anonymous_struct_info = self._copy_anonymous_struct_info(
                            field.array_info.element_anonymous_struct_info
                        )
                    return field.resolved_type
                raise ZincTypeError(f"anonymous struct has no field '{member_name}'")
            if struct_qualified_name and struct is not None:
                raise ZincTypeError(f"struct '{struct.name}' has no member '{member_name}'")

        if receiver_type == BaseType.ENUM:
            enum_name = receiver_symbol.exact_type if receiver_symbol else None
            if enum_name:
                enum = self._analyze_enum_by_qualified_name(enum_name)
                raise ZincTypeError(f"enum '{enum.name}' has no member '{member_name}'")

        self.symbols.define_temp(
            resolved_type=BaseType.UNKNOWN,
            interval=ctx.getSourceInterval(),
        )
        return BaseType.UNKNOWN

    def visitFunctionCallExpr(self, ctx: ZincParser.FunctionCallExprContext) -> BaseType:
        """Visit function call expression and create specialization if needed."""
        callee_ctx = ctx.expression()
        if isinstance(callee_ctx, ZincParser.PrimaryExprContext):
            primary = callee_ctx.primaryExpression()
            if primary and primary.IDENTIFIER():
                builtin_name = primary.IDENTIFIER().getText()
                args = list(ctx.argumentList().expression()) if ctx.argumentList() else []
                if builtin_name == "line":
                    if args:
                        raise ZincTypeError("line() does not accept arguments")
                    symbol = self._record_constant_value(
                        ctx.getSourceInterval(),
                        ctx.start.line if ctx.start is not None else 0,
                        line_num=ctx.start.line if ctx.start is not None else 0,
                    )
                    symbol.exact_type = "u32"
                    return symbol.resolved_type
                if builtin_name == "meta":
                    if len(args) != 1:
                        raise ZincTypeError("meta() expects exactly one argument")
                    meta_value = self._meta_from_expression(args[0])
                    self._record_constant_value(
                        ctx.getSourceInterval(),
                        meta_value,
                        line_num=ctx.start.line if ctx.start is not None else 0,
                    )
                    return BaseType.STRUCT
                if builtin_name == "type":
                    if len(args) != 1:
                        raise ZincTypeError("type() expects exactly one argument")
                    type_meta = self._type_meta_from_expr_ctx(args[0])
                    self._record_constant_value(
                        ctx.getSourceInterval(),
                        type_meta,
                        line_num=ctx.start.line if ctx.start is not None else 0,
                    )
                    return BaseType.STRUCT
                if builtin_name == "has_component":
                    if len(args) != 2:
                        raise ZincTypeError("has_component() expects exactly two arguments")
                    actual = self._type_meta_from_expr_ctx(args[0])
                    expected = self._type_meta_from_expr_ctx(args[1])
                    self._record_constant_value(
                        ctx.getSourceInterval(),
                        self._has_component_from_types(actual, expected),
                        line_num=ctx.start.line if ctx.start is not None else 0,
                    )
                    return BaseType.BOOLEAN
                if builtin_name == "implements":
                    if len(args) != 2:
                        raise ZincTypeError("implements() expects exactly two arguments")
                    actual = self._type_meta_from_expr_ctx(args[0])
                    expected = self._type_meta_from_expr_ctx(args[1])
                    self._record_constant_value(
                        ctx.getSourceInterval(),
                        self._implements_from_types(actual, expected),
                        line_num=ctx.start.line if ctx.start is not None else 0,
                    )
                    return BaseType.BOOLEAN

        callee_type = self.visit(ctx.expression())
        if callee_type == BaseType.NEVER:
            self.symbols.define_temp(
                resolved_type=BaseType.NEVER,
                interval=ctx.getSourceInterval(),
            )
            return BaseType.NEVER

        callee_symbol = self._expr_symbol(ctx.expression())
        if (
            callee_symbol
            and isinstance(callee_symbol.constant_value, tuple)
            and len(callee_symbol.constant_value) == 3
            and callee_symbol.constant_value[0] == "__meta_method__"
        ):
            _tag, meta_value, method_name = callee_symbol.constant_value
            method_args: list[object] = []
            if ctx.argumentList():
                for arg_ctx in ctx.argumentList().expression():
                    self.visit(arg_ctx)
                    arg_symbol = self._expr_symbol(arg_ctx)
                    method_args.append(arg_symbol.constant_value if arg_symbol else None)
            result = meta_value.call_method(method_name, method_args)
            symbol = self._record_constant_value(
                ctx.getSourceInterval(),
                result,
                line_num=ctx.start.line if ctx.start is not None else 0,
            )
            return symbol.resolved_type

        # Collect argument types and array info
        arg_types: list[BaseType] = []
        arg_exact_types: list[str | None] = []
        arg_exprs: list = []
        arg_channel_infos: dict[int, ChannelTypeInfo] = {}
        arg_array_infos: dict[int, ArrayTypeInfo] = {}
        arg_dict_infos: dict[int, DictTypeInfo] = {}
        arg_set_infos: dict[int, SetTypeInfo] = {}
        arg_tuple_infos: dict[int, TupleTypeInfo] = {}
        arg_callable_infos: dict[int, CallableTypeInfo] = {}
        arg_struct_qualified_names: dict[int, str] = {}
        arg_anonymous_struct_infos: dict[int, AnonymousStructTypeInfo] = {}
        if ctx.argumentList():
            for i, arg_expr in enumerate(ctx.argumentList().expression()):
                arg_exprs.append(arg_expr)
                arg_type = self.visit(arg_expr)
                if arg_type == BaseType.NEVER:
                    self.symbols.define_temp(
                        resolved_type=BaseType.NEVER,
                        interval=ctx.getSourceInterval(),
                    )
                    return BaseType.NEVER
                arg_types.append(arg_type)
                arg_symbol = self._expr_symbol(arg_expr)
                arg_exact_types.append(
                    arg_symbol.exact_type if arg_symbol else self._resolved_exact_type(arg_type, None)
                )

                if arg_type == BaseType.CHANNEL:
                    if isinstance(arg_expr, ZincParser.PrimaryExprContext):
                        primary = arg_expr.primaryExpression()
                        if primary and primary.IDENTIFIER():
                            chan_var = primary.IDENTIFIER().getText()
                            if chan_var in self._channel_infos:
                                arg_channel_infos[i] = self._channel_infos[chan_var]
                                continue
                    if arg_symbol and arg_symbol.channel_info:
                        arg_channel_infos[i] = self._copy_channel_info(arg_symbol.channel_info) or ChannelTypeInfo()
                # Track array element types for array arguments
                elif arg_type == BaseType.ARRAY:
                    if arg_symbol and arg_symbol.element_type:
                        copied_array = self._array_info_from_symbol(arg_symbol)
                        if copied_array is not None:
                            arg_array_infos[i] = copied_array
                    elif isinstance(arg_expr, ZincParser.PrimaryExprContext):
                        primary = arg_expr.primaryExpression()
                        if primary and primary.IDENTIFIER():
                            arr_var = primary.IDENTIFIER().getText()
                            arr_symbol = self.symbols.lookup_by_id(arr_var)
                            if arr_symbol and arr_symbol.element_type:
                                copied_array = self._array_info_from_symbol(arr_symbol)
                                if copied_array is not None:
                                    arg_array_infos[i] = copied_array
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
                    if arg_symbol and arg_symbol.tuple_info:
                        copied = self._copy_tuple_info(arg_symbol.tuple_info)
                        if copied:
                            arg_tuple_infos[i] = copied
                elif arg_type == BaseType.CALLABLE:
                    if arg_symbol and arg_symbol.callable_info:
                        arg_callable_infos[i] = self._copy_callable_info(arg_symbol.callable_info) or CallableTypeInfo()
                elif arg_type == BaseType.STRUCT:
                    if arg_symbol:
                        struct_qualified_name, anonymous_struct_info = self._struct_metadata_for_symbol(arg_symbol)
                        if struct_qualified_name is not None:
                            arg_struct_qualified_names[i] = struct_qualified_name
                        if anonymous_struct_info is not None:
                            arg_anonymous_struct_infos[i] = self._copy_anonymous_struct_info(
                                anonymous_struct_info
                            ) or AnonymousStructTypeInfo()

        if isinstance(callee_ctx, ZincParser.PrimaryExprContext):
            primary = callee_ctx.primaryExpression()
            if primary and primary.IDENTIFIER():
                lexical_function = self._current_lexical_function(primary.IDENTIFIER().getText())
                if lexical_function is not None and BaseType.UNKNOWN not in arg_types:
                    self._validate_constraints(
                        lexical_function.ctx,
                        self._constraint_slots_from_call(
                            lexical_function.ctx,
                            arg_types,
                            arg_exact_types,
                            arg_array_infos,
                            arg_dict_infos,
                            arg_set_infos,
                            arg_tuple_infos,
                            arg_callable_infos,
                            arg_struct_qualified_names,
                            arg_anonymous_struct_infos,
                        ),
                        label=f"call to '{lexical_function.display_name}'",
                    )
                    self._validate_annotated_parameters(
                        lexical_function.ctx,
                        arg_types,
                        arg_exact_types,
                        arg_exprs,
                        arg_array_infos,
                        arg_dict_infos,
                        arg_set_infos,
                        arg_tuple_infos,
                        arg_callable_infos,
                        arg_struct_qualified_names,
                        arg_anonymous_struct_infos,
                    )
                    mangled = self.atlas.add_specialization(
                        lexical_function.qualified_name,
                        arg_types,
                        arg_exact_types,
                        lexical_function.ctx,
                        self._current_function,
                        arg_channel_infos,
                        arg_array_infos,
                        arg_dict_infos,
                        arg_set_infos,
                        arg_tuple_infos,
                        arg_callable_infos,
                        arg_struct_qualified_names,
                        arg_anonymous_struct_infos,
                    )
                    key = (self._current_function, ctx.getSourceInterval())
                    self.specialization_map[key] = mangled
                    func_instance = self.atlas.functions.get(mangled)
                    if func_instance:
                        for idx, chan_info in arg_channel_infos.items():
                            func_instance.arg_channel_infos.setdefault(idx, [])
                            if all(existing is not chan_info for existing in func_instance.arg_channel_infos[idx]):
                                func_instance.arg_channel_infos[idx].append(chan_info)
                    if func_instance is not None:
                        self._record_value_info(
                            ctx.getSourceInterval(),
                            ResolvedValueInfo(
                                base_type=func_instance.return_type,
                                exact_type=func_instance.return_exact_type,
                                dict_info=self._copy_dict_info(func_instance.return_dict_info),
                                set_info=self._copy_set_info(func_instance.return_set_info),
                                tuple_info=self._copy_tuple_info(func_instance.return_tuple_info),
                                callable_info=self._copy_callable_info(func_instance.return_callable_info),
                                struct_qualified_name=func_instance.return_struct_qualified_name,
                                anonymous_struct_info=self._copy_anonymous_struct_info(
                                    func_instance.return_anonymous_struct_info
                                ),
                            ),
                        )
                        return func_instance.return_type

        if isinstance(callee_ctx, ZincParser.PrimaryExprContext):
            primary = callee_ctx.primaryExpression()
            if primary and primary.IDENTIFIER():
                func_name = primary.IDENTIFIER().getText()
                if func_name == "chan":
                    if len(arg_types) > 1:
                        raise ZincTypeError("chan() accepts at most one capacity argument")
                    if arg_types and arg_types[0] != BaseType.INTEGER:
                        raise ZincTypeError("chan() capacity must be an integer")
                    temp = self.symbols.define_temp(
                        resolved_type=BaseType.CHANNEL,
                        interval=ctx.getSourceInterval(),
                    )
                    temp.channel_info = ChannelTypeInfo(
                        element_type=BaseType.UNKNOWN,
                        is_bounded=bool(arg_types),
                    )
                    return BaseType.CHANNEL
                if func_name == "close":
                    if len(arg_types) != 1:
                        raise ZincTypeError("close() expects exactly one channel argument")
                    if arg_types[0] != BaseType.CHANNEL:
                        raise ZincTypeError("close() expects a channel argument")
                    self.symbols.define_temp(
                        resolved_type=BaseType.VOID,
                        interval=ctx.getSourceInterval(),
                    )
                    return BaseType.VOID
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
            path = extract_identifier_path(callee_ctx) if self._current_module is not None else None

            if path == ["Context", "background"]:
                if arg_types:
                    raise ZincTypeError("Context.background() does not accept arguments")
                self.symbols.define_temp(
                    resolved_type=BaseType.CONTEXT,
                    interval=ctx.getSourceInterval(),
                )
                return BaseType.CONTEXT

            if path == ["Context", "with_cancel"]:
                if len(arg_types) != 1 or arg_types[0] != BaseType.CONTEXT:
                    raise ZincTypeError("Context.with_cancel() expects a context argument")
                temp = self.symbols.define_temp(
                    resolved_type=BaseType.TUPLE,
                    interval=ctx.getSourceInterval(),
                )
                temp.tuple_info = TupleTypeInfo(
                    element_types=[BaseType.CONTEXT, BaseType.CALLABLE],
                    element_exact_types=[default_exact_type(BaseType.CONTEXT), None],
                    element_callable_infos={1: self._context_cancel_callable_info()},
                )
                return BaseType.TUPLE

            receiver_type = self.visit(receiver_ctx)
            if receiver_type == BaseType.CONTEXT:
                if method_name == "done":
                    if arg_types:
                        raise ZincTypeError("Context.done() does not accept arguments")
                    temp = self.symbols.define_temp(
                        resolved_type=BaseType.CHANNEL,
                        interval=ctx.getSourceInterval(),
                    )
                    temp.channel_info = ChannelTypeInfo(
                        element_type=BaseType.BOOLEAN,
                        element_exact_type=default_exact_type(BaseType.BOOLEAN),
                    )
                    return BaseType.CHANNEL
                if method_name == "cancel":
                    if arg_types:
                        raise ZincTypeError("Context.cancel() does not accept arguments")
                    self.symbols.define_temp(
                        resolved_type=BaseType.VOID,
                        interval=ctx.getSourceInterval(),
                    )
                    return BaseType.VOID

            # len() always returns an integer (usize in Rust, i64 in Zinc)
            if method_name == "len":
                self.symbols.define_temp(
                    resolved_type=BaseType.INTEGER,
                    interval=ctx.getSourceInterval(),
                    exact_type=default_exact_type(BaseType.INTEGER),
                )
                return BaseType.INTEGER

            if method_name in {"is_empty", "contains", "contains_key"}:
                self.symbols.define_temp(
                    resolved_type=BaseType.BOOLEAN,
                    interval=ctx.getSourceInterval(),
                    exact_type=default_exact_type(BaseType.BOOLEAN),
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
                            arg_symbol = self._expr_symbol(arg_exprs[0])
                            if var_symbol.element_type is None:
                                var_symbol.element_type = arg_types[0]
                            var_symbol.element_exact_type = self._merge_exact_type_for_base(
                                var_symbol.element_exact_type,
                                arg_symbol.exact_type if arg_symbol else None,
                                var_symbol.element_type,
                                "array element",
                            )
                            if arg_types[0] == BaseType.STRUCT and arg_symbol:
                                var_symbol.element_struct_qualified_name = self._struct_qualified_name_for_symbol(
                                    arg_symbol
                                )
                                var_symbol.element_anonymous_struct_info = self._copy_anonymous_struct_info(
                                    arg_symbol.anonymous_struct_info
                                )
                            if arg_types[0] == BaseType.TUPLE:
                                if arg_symbol and arg_symbol.tuple_info:
                                    var_symbol.tuple_info = self._copy_tuple_info(arg_symbol.tuple_info)
                            if arg_types[0] == BaseType.CALLABLE:
                                var_symbol.callable_info = self._merge_callable_info(
                                    var_symbol.callable_info,
                                    arg_symbol.callable_info if arg_symbol else None,
                                    "array element",
                                )

                        if var_symbol.resolved_type == BaseType.DICT and var_symbol.dict_info:
                            dict_info = var_symbol.dict_info
                            if method_name == "insert":
                                if len(arg_types) != 2:
                                    raise ZincTypeError("dict.insert() expects key and value arguments")
                                if arg_types[0] == BaseType.CALLABLE:
                                    raise ZincTypeError("callables cannot be used as dict keys")
                                key_symbol = self._expr_symbol(arg_exprs[0])
                                value_symbol = self._expr_symbol(arg_exprs[1])
                                dict_info.key_type = self._merge_key_type(dict_info.key_type, arg_types[0], "dict key")
                                dict_info.value_type = self._merge_value_type(
                                    dict_info.value_type, arg_types[1], "dict value"
                                )
                                dict_info.key_exact_type = self._merge_exact_type_for_base(
                                    dict_info.key_exact_type,
                                    key_symbol.exact_type if key_symbol else None,
                                    dict_info.key_type,
                                    "dict key",
                                )
                                dict_info.value_exact_type = self._merge_exact_type_for_base(
                                    dict_info.value_exact_type,
                                    value_symbol.exact_type if value_symbol else None,
                                    dict_info.value_type,
                                    "dict value",
                                )
                                if arg_types[0] == BaseType.STRUCT and key_symbol:
                                    dict_info.key_struct_qualified_name = self._struct_qualified_name_for_symbol(
                                        key_symbol
                                    )
                                    dict_info.key_anonymous_struct_info = self._copy_anonymous_struct_info(
                                        key_symbol.anonymous_struct_info
                                    )
                                if arg_types[1] == BaseType.STRUCT and value_symbol:
                                    dict_info.value_struct_qualified_name = self._struct_qualified_name_for_symbol(
                                        value_symbol
                                    )
                                    dict_info.value_anonymous_struct_info = self._copy_anonymous_struct_info(
                                        value_symbol.anonymous_struct_info
                                    )
                                if arg_types[1] == BaseType.CALLABLE:
                                    dict_info.value_callable_info = self._merge_callable_info(
                                        dict_info.value_callable_info,
                                        value_symbol.callable_info if value_symbol else None,
                                        "dict value",
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
                                symbol.element_exact_type = dict_info.key_exact_type
                                symbol.element_struct_qualified_name = dict_info.key_struct_qualified_name
                                symbol.element_anonymous_struct_info = self._copy_anonymous_struct_info(
                                    dict_info.key_anonymous_struct_info
                                )
                                return BaseType.ARRAY
                            elif method_name == "values":
                                if arg_types:
                                    raise ZincTypeError("dict.values() does not accept arguments")
                                symbol = self.symbols.define_temp(
                                    resolved_type=BaseType.ARRAY,
                                    interval=ctx.getSourceInterval(),
                                )
                                symbol.element_type = dict_info.value_type
                                symbol.element_exact_type = dict_info.value_exact_type
                                symbol.callable_info = self._copy_callable_info(dict_info.value_callable_info)
                                symbol.element_struct_qualified_name = dict_info.value_struct_qualified_name
                                symbol.element_anonymous_struct_info = self._copy_anonymous_struct_info(
                                    dict_info.value_anonymous_struct_info
                                )
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
                                temp = self.symbols.define_temp(
                                    resolved_type=dict_info.value_type,
                                    interval=ctx.getSourceInterval(),
                                    exact_type=dict_info.value_exact_type,
                                )
                                temp.callable_info = self._copy_callable_info(dict_info.value_callable_info)
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
                                if arg_types[0] == BaseType.CALLABLE:
                                    raise ZincTypeError("callables cannot be used as set elements")
                                elem_symbol = self._expr_symbol(arg_exprs[0])
                                set_info.element_type = self._merge_key_type(
                                    set_info.element_type, arg_types[0], "set element"
                                )
                                set_info.element_exact_type = self._merge_exact_type_for_base(
                                    set_info.element_exact_type,
                                    elem_symbol.exact_type if elem_symbol else None,
                                    set_info.element_type,
                                    "set element",
                                )
                                if arg_types[0] == BaseType.STRUCT and elem_symbol:
                                    set_info.element_struct_qualified_name = self._struct_qualified_name_for_symbol(
                                        elem_symbol
                                    )
                                    set_info.element_anonymous_struct_info = self._copy_anonymous_struct_info(
                                        elem_symbol.anonymous_struct_info
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

        callee_symbol = self._expr_symbol(callee_ctx)
        is_bare_top_level_function = False
        is_direct_static_method = False
        if self._current_module is not None:
            path = extract_identifier_path(callee_ctx)
            if path:
                is_direct_static_method = (
                    self.module_graph.resolve_static_method_target(self._current_module, path) is not None
                )
                if len(path) == 1:
                    local_symbol = self.symbols.lookup_by_id(path[0])
                    is_bare_top_level_function = (
                        self.module_graph.resolve_function_path(self._current_module, path) is not None
                        and local_symbol is None
                    )
        if (
            callee_symbol
            and callee_symbol.resolved_type == BaseType.CALLABLE
            and callee_symbol.callable_info
            and not is_bare_top_level_function
            and not is_direct_static_method
        ):
            callable_info = callee_symbol.callable_info
            if len(callable_info.param_types) != len(arg_types):
                raise ZincTypeError("indirect call arity mismatch")

            return_type = BaseType.UNKNOWN
            return_exact_type = None
            return_dict_info = None
            return_set_info = None
            return_tuple_info = None
            return_callable_info = None
            return_struct_qualified_name = None
            return_anonymous_struct_info = None

            for target in callable_info.targets:
                candidate_type = BaseType.UNKNOWN
                candidate_exact_type = None
                candidate_dict_info = None
                candidate_set_info = None
                candidate_tuple_info = None
                candidate_callable_info = None
                candidate_struct_qualified_name = None
                candidate_anonymous_struct_info = None

                if target.kind == "context_cancel":
                    candidate_type = BaseType.VOID
                elif target.kind in {"function", "lambda", "closure"}:
                    func_def = self.atlas.function_defs.get(target.qualified_name)
                    if func_def is None:
                        raise ZincTypeError(f"unknown callable target '{target.display_name}'")
                    if BaseType.UNKNOWN not in arg_types:
                        self._validate_annotated_parameters(
                            func_def,
                            arg_types,
                            arg_exact_types,
                            arg_exprs,
                            arg_array_infos,
                            arg_dict_infos,
                            arg_set_infos,
                            arg_tuple_infos,
                            arg_callable_infos,
                            arg_struct_qualified_names,
                            arg_anonymous_struct_infos,
                        )
                        mangled = self.atlas.add_specialization(
                            target.qualified_name,
                            arg_types,
                            arg_exact_types,
                            func_def,
                            self._current_function,
                            arg_channel_infos,
                            arg_array_infos,
                            arg_dict_infos,
                            arg_set_infos,
                            arg_tuple_infos,
                            arg_callable_infos,
                            arg_struct_qualified_names,
                            arg_anonymous_struct_infos,
                        )
                        func_instance = self.atlas.functions.get(mangled)
                        if func_instance:
                            candidate_type = func_instance.return_type
                            candidate_exact_type = func_instance.return_exact_type
                            candidate_dict_info = func_instance.return_dict_info
                            candidate_set_info = func_instance.return_set_info
                            candidate_tuple_info = func_instance.return_tuple_info
                            candidate_callable_info = func_instance.return_callable_info
                            candidate_struct_qualified_name = func_instance.return_struct_qualified_name
                            candidate_anonymous_struct_info = self._copy_anonymous_struct_info(
                                func_instance.return_anonymous_struct_info
                            )
                else:
                    owner_qualified_name = (
                        target.receiver_struct_qualified_name
                        or target.qualified_name.partition("::")[0]
                    )
                    method_name = target.qualified_name.rpartition("::")[2]
                    owner_symbol = self.module_graph.get_symbol(owner_qualified_name)
                    if owner_symbol.kind == "struct":
                        owner = self.atlas.structs.get(owner_qualified_name)
                    elif owner_symbol.kind == "enum":
                        owner = self._analyze_enum_by_qualified_name(owner_qualified_name)
                    else:
                        owner = None
                    if owner is None:
                        raise ZincTypeError(f"unknown callable target '{target.display_name}'")
                    method = next((candidate for candidate in owner.methods if candidate.name == method_name), None)
                    if method is None:
                        raise ZincTypeError(f"unknown callable target '{target.display_name}'")
                    return_info = self._resolved_named_type_info(
                        method.return_type,
                        source_module_id=method.source_module_id or owner_symbol.module_id,
                        owner_qualified_name=owner_qualified_name,
                        owner_kind=owner_symbol.kind,
                    )
                    candidate_type = return_info.base_type
                    candidate_exact_type = return_info.exact_type
                    candidate_struct_qualified_name = return_info.struct_qualified_name
                    candidate_anonymous_struct_info = self._copy_anonymous_struct_info(
                        return_info.anonymous_struct_info
                    )

                if candidate_type == BaseType.UNKNOWN:
                    continue
                if return_type == BaseType.UNKNOWN:
                    return_type = candidate_type
                    return_exact_type = candidate_exact_type
                    return_dict_info = self._copy_dict_info(candidate_dict_info)
                    return_set_info = self._copy_set_info(candidate_set_info)
                    return_tuple_info = self._copy_tuple_info(candidate_tuple_info)
                    return_callable_info = self._copy_callable_info(candidate_callable_info)
                    return_struct_qualified_name = candidate_struct_qualified_name
                    return_anonymous_struct_info = self._copy_anonymous_struct_info(
                        candidate_anonymous_struct_info
                    )
                    continue
                promoted = promote_numeric(return_type, candidate_type)
                if promoted == BaseType.UNKNOWN and candidate_type != return_type:
                    raise ZincTypeError("indirect call targets disagree on return type")
                return_type = promoted
                return_exact_type = promote_exact_numeric(return_exact_type, candidate_exact_type, return_type)
                if return_type == BaseType.DICT:
                    return_dict_info = self._merge_dict_info(return_dict_info, candidate_dict_info)
                if return_type == BaseType.SET:
                    return_set_info = self._merge_set_info(return_set_info, candidate_set_info)
                if return_type == BaseType.TUPLE:
                    return_tuple_info = self._merge_tuple_info(return_tuple_info, candidate_tuple_info)
                if return_type == BaseType.CALLABLE:
                    return_callable_info = self._merge_callable_info(
                        return_callable_info,
                        candidate_callable_info,
                        "callable return",
                    )
                if return_type == BaseType.STRUCT:
                    if not self._structs_compatible(
                        return_struct_qualified_name,
                        return_anonymous_struct_info,
                        candidate_struct_qualified_name,
                        candidate_anonymous_struct_info,
                    ):
                        raise ZincTypeError("indirect call targets disagree on return type")
                    if return_struct_qualified_name is None:
                        return_struct_qualified_name = candidate_struct_qualified_name
                    if return_anonymous_struct_info is None and candidate_anonymous_struct_info is not None:
                        return_anonymous_struct_info = self._copy_anonymous_struct_info(
                            candidate_anonymous_struct_info
                        )

            self._refine_callable_signature(
                callable_info,
                arg_types,
                arg_exact_types,
                arg_array_infos,
                arg_dict_infos,
                arg_set_infos,
                arg_tuple_infos,
                arg_callable_infos,
                arg_struct_qualified_names,
                arg_anonymous_struct_infos,
                return_type,
                return_exact_type,
                return_dict_info,
                return_set_info,
                return_tuple_info,
                return_callable_info,
                return_struct_qualified_name,
                return_anonymous_struct_info,
            )
            temp = self.symbols.define_temp(
                resolved_type=return_type,
                interval=ctx.getSourceInterval(),
                exact_type=return_exact_type,
            )
            temp.dict_info = self._copy_dict_info(return_dict_info)
            temp.set_info = self._copy_set_info(return_set_info)
            temp.tuple_info = self._copy_tuple_info(return_tuple_info)
            temp.callable_info = return_callable_info
            temp.anonymous_struct_info = self._copy_anonymous_struct_info(return_anonymous_struct_info)
            if return_struct_qualified_name is not None:
                self._struct_symbol_bindings[temp.unique_name] = return_struct_qualified_name
            return return_type

        path = extract_identifier_path(callee_ctx)
        if path and self._current_module is not None:
            static_target = self.module_graph.resolve_static_method_target(self._current_module, path)
            if static_target:
                owner_symbol, method_name = static_target
                if owner_symbol.kind == "struct":
                    owner = self.atlas.structs.get(owner_symbol.qualified_name)
                elif owner_symbol.kind == "enum":
                    owner = self._analyze_enum_by_qualified_name(owner_symbol.qualified_name)
                else:
                    owner = None
                if owner:
                    method = next((candidate for candidate in owner.methods if candidate.name == method_name), None)
                    if method:
                        if not method.is_static:
                            raise ZincTypeError("instance methods must be bound to a receiver before use as callable values")
                        return_info = self._resolved_named_type_info(
                            method.return_type,
                            source_module_id=method.source_module_id or owner_symbol.module_id,
                            owner_qualified_name=owner_symbol.qualified_name,
                            owner_kind=owner_symbol.kind,
                        )
                        self._record_value_info(ctx.getSourceInterval(), return_info)
                        return return_info.base_type

            resolved_function = self.module_graph.resolve_function_path(self._current_module, path)
            if resolved_function and resolved_function.name not in (
                "print",
                "chan",
                "close",
                "dict",
                "sort_dict",
                "set",
                "sort_set",
                "meta",
                "type",
                "line",
                "has_component",
                "implements",
            ):
                func_def = self.atlas.function_defs.get(resolved_function.qualified_name)
                if func_def and BaseType.UNKNOWN not in arg_types:
                    self._validate_constraints(
                        func_def,
                        self._constraint_slots_from_call(
                            func_def,
                            arg_types,
                            arg_exact_types,
                            arg_array_infos,
                            arg_dict_infos,
                            arg_set_infos,
                            arg_tuple_infos,
                            arg_callable_infos,
                            arg_struct_qualified_names,
                            arg_anonymous_struct_infos,
                        ),
                        label=f"call to '{resolved_function.name}'",
                    )
                    self._validate_annotated_parameters(
                        func_def,
                        arg_types,
                        arg_exact_types,
                        arg_exprs,
                        arg_array_infos,
                        arg_dict_infos,
                        arg_set_infos,
                        arg_tuple_infos,
                        arg_callable_infos,
                        arg_struct_qualified_names,
                        arg_anonymous_struct_infos,
                    )
                    mangled = self.atlas.add_specialization(
                        resolved_function.qualified_name,
                        arg_types,
                        arg_exact_types,
                        func_def,
                        self._current_function,
                        arg_channel_infos,
                        arg_array_infos,
                        arg_dict_infos,
                        arg_set_infos,
                        arg_tuple_infos,
                        arg_callable_infos,
                        arg_struct_qualified_names,
                        arg_anonymous_struct_infos,
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
                    if func_instance:
                        self._record_value_info(
                            ctx.getSourceInterval(),
                            ResolvedValueInfo(
                                base_type=func_instance.return_type,
                                exact_type=func_instance.return_exact_type,
                                dict_info=self._copy_dict_info(func_instance.return_dict_info),
                                set_info=self._copy_set_info(func_instance.return_set_info),
                                tuple_info=self._copy_tuple_info(func_instance.return_tuple_info),
                                callable_info=self._copy_callable_info(func_instance.return_callable_info),
                                struct_qualified_name=func_instance.return_struct_qualified_name,
                                anonymous_struct_info=self._copy_anonymous_struct_info(
                                    func_instance.return_anonymous_struct_info
                                ),
                            ),
                        )
                        return func_instance.return_type

            if len(path) == 1:
                func_symbol = self.symbols.lookup_by_id(path[0])
                if func_symbol:
                    self.symbols.define_temp(
                        resolved_type=func_symbol.resolved_type,
                        interval=ctx.getSourceInterval(),
                        exact_type=func_symbol.exact_type,
                    )
                    return func_symbol.resolved_type

        self.symbols.define_temp(
            resolved_type=BaseType.UNKNOWN,
            interval=ctx.getSourceInterval(),
        )
        return BaseType.UNKNOWN

    def visitTypedVariableAssignment(self, ctx: ZincParser.TypedVariableAssignmentContext) -> None:
        """Visit a typed local declaration and enforce the annotation strictly."""
        expr_type = self.visit(ctx.expression())
        var_name = ctx.IDENTIFIER().getText()
        existing = self.symbols.lookup_by_id(var_name)

        expr_symbol = self._expr_symbol(ctx.expression())
        expr_exact_type = expr_symbol.exact_type if expr_symbol else self._resolved_exact_type(expr_type, None)
        expr_constant_value = expr_symbol.constant_value if expr_symbol else None
        expr_channel_info = self._copy_channel_info(expr_symbol.channel_info) if expr_symbol else None
        expr_array_info = self._array_info_from_symbol(expr_symbol)
        expr_dict_info = self._copy_dict_info(expr_symbol.dict_info) if expr_symbol else None
        expr_set_info = self._copy_set_info(expr_symbol.set_info) if expr_symbol else None
        expr_tuple_info = self._copy_tuple_info(expr_symbol.tuple_info) if expr_symbol else None
        expr_callable_info = self._copy_callable_info(expr_symbol.callable_info) if expr_symbol else None
        expr_struct_qualified_name = self._struct_qualified_name_for_symbol(expr_symbol)
        expr_anonymous_struct_info = self._copy_anonymous_struct_info(
            expr_symbol.anonymous_struct_info if expr_symbol else None
        )

        (
            annotated_type,
            annotated_array_info,
            annotated_dict_info,
            annotated_set_info,
            annotated_tuple_info,
            annotated_callable_info,
            annotated_struct_qualified_name,
            annotated_anonymous_struct_info,
        ) = self._type_metadata_from_type_ctx(ctx.type_())
        declared_exact_type = self._exact_type_name_from_type_ctx(ctx.type_())

        if not self._assignment_metadata_compatible(
            annotated_type,
            expr_type,
            expected_exact_type=declared_exact_type,
            actual_exact_type=expr_exact_type,
            actual_constant_value=self._literal_constant_value_for_expr(ctx.expression(), expr_symbol),
            expected_array=annotated_array_info,
            actual_array=expr_array_info,
            expected_dict=annotated_dict_info,
            actual_dict=expr_dict_info,
            expected_set=annotated_set_info,
            actual_set=expr_set_info,
            expected_tuple=annotated_tuple_info,
            actual_tuple=expr_tuple_info,
            expected_callable=annotated_callable_info,
            actual_callable=expr_callable_info,
            expected_struct_qualified_name=annotated_struct_qualified_name,
            actual_struct_qualified_name=expr_struct_qualified_name,
            expected_anonymous_struct_info=annotated_anonymous_struct_info,
            actual_anonymous_struct_info=expr_anonymous_struct_info,
        ):
            expected_label = declared_exact_type or ctx.type_().getText()
            raise ZincTypeError(
                f"variable '{var_name}' expects a compatible '{expected_label}' value"
            )

        new_sym = self.symbols.define(
            id=var_name,
            kind=SymbolKind.VARIABLE,
            resolved_type=annotated_type,
            interval=ctx.IDENTIFIER().getSourceInterval(),
            exact_type=declared_exact_type,
            declared_exact_type=declared_exact_type,
            has_declared_type=True,
            is_shadow=existing is not None,
            constant_value=expr_constant_value,
            line_num=ctx.start.line if ctx.start is not None else 0,
        )

        if annotated_type == BaseType.ARRAY:
            array_info = annotated_array_info or expr_array_info
            if array_info is not None:
                new_sym.element_type = array_info.element_type
                new_sym.element_exact_type = array_info.element_exact_type
                new_sym.tuple_info = self._copy_tuple_info(array_info.element_tuple_info)
                new_sym.callable_info = self._copy_callable_info(array_info.element_callable_info)
                new_sym.element_struct_qualified_name = array_info.element_struct_qualified_name
                new_sym.element_anonymous_struct_info = self._copy_anonymous_struct_info(
                    array_info.element_anonymous_struct_info
                )
        elif annotated_type == BaseType.CHANNEL:
            new_sym.channel_info = expr_channel_info
        elif annotated_type == BaseType.DICT:
            new_sym.dict_info = annotated_dict_info or expr_dict_info
        elif annotated_type == BaseType.SET:
            new_sym.set_info = annotated_set_info or expr_set_info
        elif annotated_type == BaseType.TUPLE:
            new_sym.tuple_info = annotated_tuple_info or expr_tuple_info
        elif annotated_type == BaseType.CALLABLE:
            new_sym.callable_info = self._merge_callable_info(
                annotated_callable_info,
                expr_callable_info,
                f"variable '{var_name}'",
            )
        elif annotated_type == BaseType.STRUCT:
            new_sym.anonymous_struct_info = (
                annotated_anonymous_struct_info or expr_anonymous_struct_info
            )
            struct_qualified_name = annotated_struct_qualified_name or expr_struct_qualified_name
            if struct_qualified_name is not None:
                self._struct_symbol_bindings[new_sym.unique_name] = struct_qualified_name

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
        provided_exprs: dict[str, tuple[BaseType, Symbol | None, ParserRuleContext]] = {}
        for field_ctx in ctx.fieldInit():
            field_name = field_ctx.IDENTIFIER().getText()
            if field_name in provided_exprs:
                raise ZincTypeError(f"struct literal has duplicate field '{field_name}'")
            field_type = self.visit(field_ctx.expression())
            provided_exprs[field_name] = (
                field_type,
                self._expr_symbol(field_ctx.expression()),
                field_ctx.expression(),
            )

        resolved_struct = None
        if self._current_module is not None:
            resolved_struct = self.module_graph.resolve_struct_path(
                self._current_module, struct_path_from_ctx(ctx)
            )
            if resolved_struct is None:
                raise ZincTypeError(f"unknown struct '{ctx.qualifiedName().getText()}'")
        struct_info = self.atlas.structs.get(resolved_struct.qualified_name) if resolved_struct else None
        concrete_anonymous_struct_info = None
        if struct_info is not None:
            field_map = {field.name: field for field in struct_info.fields}
            for field_name, (actual_type, actual_symbol, actual_expr_ctx) in provided_exprs.items():
                expected_field = field_map.get(field_name)
                if expected_field is None:
                    raise ZincTypeError(f"struct '{struct_info.name}' has no field '{field_name}'")
                if expected_field.is_infer:
                    continue
                actual_struct_qualified_name, actual_anonymous_struct_info = self._struct_metadata_for_symbol(actual_symbol)
                actual_array_info = self._array_info_from_symbol(actual_symbol)
                if not self._assignment_metadata_compatible(
                    expected_field.resolved_type,
                    actual_type,
                    expected_exact_type=expected_field.exact_type or self._exact_type_name_from_text(expected_field.type_annotation),
                    actual_exact_type=actual_symbol.exact_type if actual_symbol else None,
                    actual_constant_value=self._literal_constant_value_for_expr(actual_expr_ctx, actual_symbol),
                    expected_array=expected_field.array_info,
                    actual_array=actual_array_info,
                    expected_dict=expected_field.dict_info,
                    actual_dict=self._copy_dict_info(actual_symbol.dict_info) if actual_symbol else None,
                    expected_set=expected_field.set_info,
                    actual_set=self._copy_set_info(actual_symbol.set_info) if actual_symbol else None,
                    expected_tuple=expected_field.tuple_info,
                    actual_tuple=self._copy_tuple_info(actual_symbol.tuple_info) if actual_symbol else None,
                    expected_callable=expected_field.callable_info,
                    actual_callable=self._copy_callable_info(actual_symbol.callable_info) if actual_symbol else None,
                    expected_struct_qualified_name=expected_field.struct_qualified_name,
                    actual_struct_qualified_name=actual_struct_qualified_name,
                    expected_anonymous_struct_info=expected_field.anonymous_struct_info,
                    actual_anonymous_struct_info=actual_anonymous_struct_info,
                ):
                    raise ZincTypeError(
                        f"struct field '{struct_info.name}.{field_name}' expects a compatible '{expected_field.rust_type()}' value"
                    )
            concrete_fields: list[AnonymousStructFieldInfo] = []
            constraint_slots: dict[str, MetaValue] = {}
            for field in struct_info.fields:
                actual = provided_exprs.get(field.name)
                if field.is_infer and actual is None:
                    raise ZincTypeError(f"struct '{struct_info.name}' is missing infer field '{field.name}'")
                if actual is not None and field.is_infer:
                    actual_type, actual_symbol, _actual_expr_ctx = actual
                    actual_struct_qualified_name, actual_anonymous_struct_info = self._struct_metadata_for_symbol(actual_symbol)
                    concrete_fields.append(
                        AnonymousStructFieldInfo(
                            name=field.name,
                            resolved_type=actual_type,
                            exact_type=actual_symbol.exact_type if actual_symbol else default_exact_type(actual_type),
                            array_info=self._array_info_from_symbol(actual_symbol),
                            dict_info=self._copy_dict_info(actual_symbol.dict_info) if actual_symbol else None,
                            set_info=self._copy_set_info(actual_symbol.set_info) if actual_symbol else None,
                            tuple_info=self._copy_tuple_info(actual_symbol.tuple_info) if actual_symbol else None,
                            callable_info=self._copy_callable_info(actual_symbol.callable_info) if actual_symbol else None,
                            struct_qualified_name=actual_struct_qualified_name,
                            anonymous_struct_info=self._copy_anonymous_struct_info(actual_anonymous_struct_info),
                        )
                    )
                    constraint_slots[field.name] = self._type_meta_from_symbol(actual_symbol)
                    continue
                concrete_fields.append(
                    AnonymousStructFieldInfo(
                        name=field.name,
                        resolved_type=field.resolved_type,
                        exact_type=field.exact_type,
                        array_info=self._copy_array_info(field.array_info),
                        dict_info=self._copy_dict_info(field.dict_info),
                        set_info=self._copy_set_info(field.set_info),
                        tuple_info=self._copy_tuple_info(field.tuple_info),
                        callable_info=self._copy_callable_info(field.callable_info),
                        struct_qualified_name=field.struct_qualified_name,
                        anonymous_struct_info=self._copy_anonymous_struct_info(field.anonymous_struct_info),
                    )
                )
                constraint_slots[field.name] = self._type_meta_from_base(
                    field.resolved_type,
                    exact_type=field.exact_type,
                    array_info=field.array_info,
                    dict_info=field.dict_info,
                    set_info=field.set_info,
                    tuple_info=field.tuple_info,
                    callable_info=field.callable_info,
                    struct_qualified_name=field.struct_qualified_name,
                    anonymous_struct_info=field.anonymous_struct_info,
                )
            if any(field.is_infer for field in struct_info.fields):
                concrete_anonymous_struct_info = AnonymousStructTypeInfo(fields=concrete_fields)
            self._validate_constraints(
                struct_info.ctx,
                constraint_slots,
                label=f"struct '{struct_info.name}'",
            )
        temp = self.symbols.define_temp(
            resolved_type=BaseType.STRUCT,
            interval=ctx.getSourceInterval(),
        )
        if resolved_struct is not None:
            self._struct_symbol_bindings[temp.unique_name] = resolved_struct.qualified_name
        if concrete_anonymous_struct_info is not None:
            temp.anonymous_struct_info = concrete_anonymous_struct_info
        return BaseType.STRUCT

    def visitAnonymousStructLiteral(self, ctx) -> BaseType:
        """Visit an anonymous struct literal."""
        seen: set[str] = set()
        fields: list[AnonymousStructFieldInfo] = []
        for field_ctx in ctx.fieldInit():
            field_name = field_ctx.IDENTIFIER().getText()
            if field_name in seen:
                raise ZincTypeError(f"anonymous struct literal has duplicate field '{field_name}'")
            seen.add(field_name)
            field_type = self.visit(field_ctx.expression())
            field_symbol = self._expr_symbol(field_ctx.expression())
            field_struct_qualified_name, field_anonymous_struct_info = self._struct_metadata_for_symbol(field_symbol)
            fields.append(
                AnonymousStructFieldInfo(
                    name=field_name,
                    resolved_type=field_type,
                    exact_type=field_symbol.exact_type if field_symbol else default_exact_type(field_type),
                    array_info=self._array_info_from_symbol(field_symbol),
                    dict_info=self._copy_dict_info(field_symbol.dict_info) if field_symbol else None,
                    set_info=self._copy_set_info(field_symbol.set_info) if field_symbol else None,
                    tuple_info=self._copy_tuple_info(field_symbol.tuple_info) if field_symbol else None,
                    callable_info=self._copy_callable_info(field_symbol.callable_info) if field_symbol else None,
                    struct_qualified_name=field_struct_qualified_name,
                    anonymous_struct_info=self._copy_anonymous_struct_info(field_anonymous_struct_info),
                )
            )
        temp = self.symbols.define_temp(
            resolved_type=BaseType.STRUCT,
            interval=ctx.getSourceInterval(),
        )
        temp.anonymous_struct_info = AnonymousStructTypeInfo(fields=fields)
        return BaseType.STRUCT

    def visitVariableAssignment(self, ctx: ZincParser.VariableAssignmentContext) -> None:
        """Visit variable assignment with shadowing support."""
        expr_type = self.visit(ctx.expression())
        target = ctx.assignmentTarget()

        if (
            target.tupleAssignmentTarget()
            and isinstance(ctx.expression(), ZincParser.ChannelReceiveExprContext)
        ):
            tokens = self._binding_tokens(target.tupleAssignmentTarget())
            if len(tokens) != 2:
                raise ZincTypeError("close-aware receive requires exactly two bindings")
            chan_info = self._channel_info_ref_for_expr(ctx.expression().expression())
            if chan_info is None:
                raise ZincTypeError("channel receive expects a channel expression")
            if chan_info.element_type == BaseType.ENUM:
                raise ZincTypeError("close-aware receive is not supported for enum channels in v1")
            binding_types = [chan_info.element_type, BaseType.BOOLEAN]
            binding_exact_types = [chan_info.element_exact_type, default_exact_type(BaseType.BOOLEAN)]
            binding_tuple_infos = [self._copy_tuple_info(chan_info.element_tuple_info), None]
            binding_callable_infos = [chan_info.element_callable_info, None]
            binding_struct_names = [chan_info.element_struct_qualified_name, None]
            binding_anonymous_struct_infos = [
                self._copy_anonymous_struct_info(chan_info.element_anonymous_struct_info),
                None,
            ]
            for i, token in enumerate(tokens):
                var_name = token.getText()
                element_type = binding_types[i]
                existing = self.symbols.lookup_by_id(var_name)
                tuple_info = binding_tuple_infos[i]
                callable_info = binding_callable_infos[i]
                struct_qualified_name = binding_struct_names[i]
                anonymous_struct_info = binding_anonymous_struct_infos[i]
                if existing is None or existing.resolved_type != element_type:
                    new_sym = self.symbols.define(
                        id=var_name,
                        kind=SymbolKind.VARIABLE,
                        resolved_type=element_type,
                        interval=token.getSourceInterval(),
                        exact_type=binding_exact_types[i],
                        is_shadow=existing is not None,
                        line_num=ctx.start.line if ctx.start is not None else 0,
                    )
                    new_sym.tuple_info = tuple_info
                    new_sym.callable_info = callable_info
                    new_sym.anonymous_struct_info = anonymous_struct_info
                    if struct_qualified_name is not None:
                        self._struct_symbol_bindings[new_sym.unique_name] = struct_qualified_name
                else:
                    existing.is_mutated = True
                    existing.tuple_info = tuple_info
                    existing.callable_info = callable_info
                    existing.anonymous_struct_info = anonymous_struct_info
                    if struct_qualified_name is not None:
                        self._struct_symbol_bindings[existing.unique_name] = struct_qualified_name
                    temp = self.symbols.define_temp(
                        resolved_type=element_type,
                        interval=token.getSourceInterval(),
                        exact_type=binding_exact_types[i],
                    )
                    temp.tuple_info = tuple_info
                    temp.callable_info = callable_info
                    temp.anonymous_struct_info = self._copy_anonymous_struct_info(anonymous_struct_info)
                    if struct_qualified_name is not None:
                        self._struct_symbol_bindings[temp.unique_name] = struct_qualified_name
            return

        if target.IDENTIFIER():
            var_name = target.IDENTIFIER().getText()
            existing = self.symbols.lookup_by_id(var_name)
            if existing is not None and existing.is_captured_ref:
                raise ZincTypeError(
                    f"assignment to captured outer variable '{var_name}' requires '<<-'"
                )

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
            expr_exact_type = expr_symbol.exact_type if expr_symbol else self._resolved_exact_type(expr_type, None)
            expr_constant_value = expr_symbol.constant_value if expr_symbol else None
            expr_channel_info = self._copy_channel_info(expr_symbol.channel_info) if expr_symbol else None
            expr_array_info = self._array_info_from_symbol(expr_symbol)
            if expr_symbol and expr_symbol.tuple_info:
                expr_tuple_info = self._copy_tuple_info(expr_symbol.tuple_info)
            expr_callable_info = (
                expr_symbol.callable_info
                if expr_type == BaseType.CALLABLE and expr_symbol
                else self._copy_callable_info(expr_symbol.callable_info) if expr_symbol else None
            )
            expr_struct_qualified_name = self._struct_qualified_name_for_symbol(expr_symbol)
            expr_anonymous_struct_info = self._copy_anonymous_struct_info(
                expr_symbol.anonymous_struct_info if expr_symbol else None
            )

            if (
                existing is not None
                and existing.is_captured_binding
                and not self._assignment_metadata_compatible(
                    existing.resolved_type,
                    expr_type,
                    expected_exact_type=existing.exact_type,
                    actual_exact_type=expr_exact_type,
                    actual_constant_value=self._literal_constant_value_for_expr(ctx.expression(), expr_symbol),
                    expected_array=self._array_info_from_symbol(existing),
                    actual_array=expr_array_info,
                    expected_dict=existing.dict_info,
                    actual_dict=expr_dict_info,
                    expected_set=existing.set_info,
                    actual_set=expr_set_info,
                    expected_tuple=existing.tuple_info,
                    actual_tuple=expr_tuple_info,
                    expected_callable=existing.callable_info,
                    actual_callable=expr_callable_info,
                    expected_struct_qualified_name=self._struct_qualified_name_for_symbol(existing),
                    actual_struct_qualified_name=expr_struct_qualified_name,
                    expected_anonymous_struct_info=existing.anonymous_struct_info,
                    actual_anonymous_struct_info=expr_anonymous_struct_info,
                )
            ):
                raise ZincTypeError(f"captured outer variable '{var_name}' cannot change type after capture")

            if (
                existing is not None
                and existing.has_declared_type
                and not self._assignment_metadata_compatible(
                    existing.resolved_type,
                    expr_type,
                    expected_exact_type=existing.declared_exact_type,
                    actual_exact_type=expr_exact_type,
                    actual_constant_value=self._literal_constant_value_for_expr(ctx.expression(), expr_symbol),
                    expected_array=self._array_info_from_symbol(existing),
                    actual_array=expr_array_info,
                    expected_dict=existing.dict_info,
                    actual_dict=expr_dict_info,
                    expected_set=existing.set_info,
                    actual_set=expr_set_info,
                    expected_tuple=existing.tuple_info,
                    actual_tuple=expr_tuple_info,
                    expected_callable=existing.callable_info,
                    actual_callable=expr_callable_info,
                    expected_struct_qualified_name=self._struct_qualified_name_for_symbol(existing),
                    actual_struct_qualified_name=expr_struct_qualified_name,
                    expected_anonymous_struct_info=existing.anonymous_struct_info,
                    actual_anonymous_struct_info=expr_anonymous_struct_info,
                )
            ):
                expected_label = existing.declared_exact_type or type_to_rust(existing.resolved_type)
                raise ZincTypeError(
                    f"variable '{var_name}' expects a compatible '{expected_label}' value"
                )

            if expr_type == BaseType.CHANNEL and expr_channel_info is not None:
                existing_channel_info = self._channel_infos.get(var_name)
                if existing_channel_info is None:
                    self._channel_infos[var_name] = self._copy_channel_info(expr_channel_info) or ChannelTypeInfo()
                else:
                    if (
                        existing_channel_info.element_type == BaseType.UNKNOWN
                        and expr_channel_info.element_type != BaseType.UNKNOWN
                    ):
                        existing_channel_info.element_type = expr_channel_info.element_type
                    existing_channel_info.element_exact_type = self._merge_exact_type_for_base(
                        existing_channel_info.element_exact_type,
                        expr_channel_info.element_exact_type,
                        existing_channel_info.element_type,
                        f"channel '{var_name}'",
                    )
                    if (
                        existing_channel_info.element_tuple_info is None
                        and expr_channel_info.element_tuple_info is not None
                    ):
                        existing_channel_info.element_tuple_info = self._copy_tuple_info(
                            expr_channel_info.element_tuple_info
                        )
                    existing_channel_info.element_callable_info = self._merge_callable_info(
                        existing_channel_info.element_callable_info,
                        expr_channel_info.element_callable_info,
                        f"channel '{var_name}'",
                    )
                    if existing_channel_info.element_struct_qualified_name is None:
                        existing_channel_info.element_struct_qualified_name = (
                            expr_channel_info.element_struct_qualified_name
                        )
                    if (
                        existing_channel_info.element_anonymous_struct_info is None
                        and expr_channel_info.element_anonymous_struct_info is not None
                    ):
                        existing_channel_info.element_anonymous_struct_info = self._copy_anonymous_struct_info(
                            expr_channel_info.element_anonymous_struct_info
                        )
                    existing_channel_info.is_bounded = expr_channel_info.is_bounded or existing_channel_info.is_bounded
                expr_channel_info = self._copy_channel_info(self._channel_infos[var_name])

            if existing is None:
                # First assignment - create new symbol
                new_sym = self.symbols.define(
                    id=var_name,
                    kind=SymbolKind.VARIABLE,
                    resolved_type=expr_type,
                    interval=target.getSourceInterval(),
                    exact_type=expr_exact_type,
                    is_shadow=False,
                    constant_value=expr_constant_value,
                    line_num=ctx.start.line if ctx.start is not None else 0,
                )
                # Propagate array element type
                if expr_element_type:
                    new_sym.element_type = expr_element_type
                    new_sym.element_exact_type = expr_array_info.element_exact_type if expr_array_info else None
                    new_sym.element_struct_qualified_name = (
                        expr_array_info.element_struct_qualified_name if expr_array_info else None
                    )
                    new_sym.element_anonymous_struct_info = (
                        self._copy_anonymous_struct_info(expr_array_info.element_anonymous_struct_info)
                        if expr_array_info
                        else None
                    )
                if expr_channel_info:
                    new_sym.channel_info = expr_channel_info
                if expr_dict_info:
                    new_sym.dict_info = expr_dict_info
                if expr_set_info:
                    new_sym.set_info = expr_set_info
                if expr_tuple_info:
                    new_sym.tuple_info = expr_tuple_info
                if expr_callable_info:
                    new_sym.callable_info = expr_callable_info
                if expr_struct_qualified_name:
                    self._struct_symbol_bindings[new_sym.unique_name] = expr_struct_qualified_name
                if expr_anonymous_struct_info is not None:
                    new_sym.anonymous_struct_info = expr_anonymous_struct_info
            elif (
                existing.resolved_type != expr_type
                or (
                    existing.declared_exact_type is None
                    and not existing.has_declared_type
                    and expr_type in {BaseType.INTEGER, BaseType.FLOAT, BaseType.STRING, BaseType.BOOLEAN, BaseType.CONTEXT}
                    and existing.exact_type is not None
                    and expr_exact_type is not None
                    and existing.exact_type != expr_exact_type
                )
                or (
                    expr_type == BaseType.STRUCT
                    and not self._structs_compatible(
                        self._struct_qualified_name_for_symbol(existing),
                        existing.anonymous_struct_info,
                        expr_struct_qualified_name,
                        expr_anonymous_struct_info,
                    )
                )
                or (
                    expr_type == BaseType.ENUM
                    and existing.exact_type is not None
                    and expr_exact_type is not None
                    and existing.exact_type != expr_exact_type
                )
            ):
                # Type change - create shadow symbol
                new_sym = self.symbols.define(
                    id=var_name,
                    kind=SymbolKind.VARIABLE,
                    resolved_type=expr_type,
                    interval=target.getSourceInterval(),
                    exact_type=expr_exact_type,
                    is_shadow=True,
                    constant_value=expr_constant_value,
                    line_num=ctx.start.line if ctx.start is not None else 0,
                )
                if expr_element_type:
                    new_sym.element_type = expr_element_type
                    new_sym.element_exact_type = expr_array_info.element_exact_type if expr_array_info else None
                    new_sym.element_struct_qualified_name = (
                        expr_array_info.element_struct_qualified_name if expr_array_info else None
                    )
                    new_sym.element_anonymous_struct_info = (
                        self._copy_anonymous_struct_info(expr_array_info.element_anonymous_struct_info)
                        if expr_array_info
                        else None
                    )
                if expr_channel_info:
                    new_sym.channel_info = expr_channel_info
                if expr_dict_info:
                    new_sym.dict_info = expr_dict_info
                if expr_set_info:
                    new_sym.set_info = expr_set_info
                if expr_tuple_info:
                    new_sym.tuple_info = expr_tuple_info
                if expr_callable_info:
                    new_sym.callable_info = expr_callable_info
                if expr_struct_qualified_name:
                    self._struct_symbol_bindings[new_sym.unique_name] = expr_struct_qualified_name
                if expr_anonymous_struct_info is not None:
                    new_sym.anonymous_struct_info = expr_anonymous_struct_info
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
                if not existing.has_declared_type:
                    existing.exact_type = expr_exact_type
                existing.constant_value = expr_constant_value
                self.symbols.define_temp(
                    resolved_type=expr_type,
                    interval=target.getSourceInterval(),
                    exact_type=expr_exact_type,
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
                if not existing.has_declared_type:
                    existing.exact_type = expr_exact_type
                existing.constant_value = expr_constant_value
                self.symbols.define_temp(
                    resolved_type=expr_type,
                    interval=target.getSourceInterval(),
                    exact_type=expr_exact_type,
                )
            elif expr_type == BaseType.TUPLE:
                if expr_tuple_info:
                    existing.tuple_info = expr_tuple_info
                existing.is_mutated = True
                self.symbols.define_temp(
                    resolved_type=expr_type,
                    interval=target.getSourceInterval(),
                    exact_type=expr_exact_type,
                )
            elif expr_type == BaseType.CHANNEL:
                existing.channel_info = self._copy_channel_info(expr_channel_info)
                existing.is_mutated = True
                temp = self.symbols.define_temp(
                    resolved_type=expr_type,
                    interval=target.getSourceInterval(),
                    exact_type=expr_exact_type,
                )
                temp.channel_info = self._copy_channel_info(existing.channel_info)
            elif expr_type == BaseType.CALLABLE:
                existing.callable_info = self._merge_callable_info(
                    existing.callable_info,
                    expr_callable_info,
                    f"variable '{var_name}'",
                )
                existing.is_mutated = True
                if not existing.has_declared_type:
                    existing.exact_type = expr_exact_type
                existing.constant_value = expr_constant_value
                temp = self.symbols.define_temp(
                    resolved_type=expr_type,
                    interval=target.getSourceInterval(),
                    exact_type=expr_exact_type,
                )
                temp.callable_info = self._copy_callable_info(existing.callable_info)
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
                    exact_type=expr_exact_type,
                    is_shadow=True,
                    constant_value=expr_constant_value,
                )
            else:
                # Same type reassignment - mark original as mutated
                existing.is_mutated = True
                if not existing.has_declared_type:
                    existing.exact_type = expr_exact_type
                existing.constant_value = expr_constant_value
                if expr_type == BaseType.ARRAY:
                    existing.callable_info = self._merge_callable_info(
                        existing.callable_info,
                        expr_callable_info,
                        f"array '{var_name}'",
                    )
                    if expr_array_info is not None:
                        existing.element_exact_type = expr_array_info.element_exact_type
                        existing.element_struct_qualified_name = expr_array_info.element_struct_qualified_name
                        existing.element_anonymous_struct_info = self._copy_anonymous_struct_info(
                            expr_array_info.element_anonymous_struct_info
                        )
                if expr_type == BaseType.STRUCT and expr_struct_qualified_name:
                    self._struct_symbol_bindings[existing.unique_name] = expr_struct_qualified_name
                if expr_type == BaseType.STRUCT:
                    existing.anonymous_struct_info = expr_anonymous_struct_info
                # Still create entry in _by_interval for this assignment
                self.symbols.define_temp(
                    resolved_type=expr_type,
                    interval=target.getSourceInterval(),
                    exact_type=expr_exact_type,
                )
        elif target.memberAccess():
            member_ctx = target.memberAccess()
            receiver_ctx = member_ctx.expression()
            if isinstance(receiver_ctx, ZincParser.PrimaryExprContext):
                primary = receiver_ctx.primaryExpression()
                if primary and primary.IDENTIFIER():
                    receiver_symbol = self.symbols.lookup_by_id(primary.IDENTIFIER().getText())
                    if receiver_symbol is not None:
                        receiver_symbol.is_mutated = True
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
                new_callable_info = self._copy_callable_info(tuple_info.element_callable_infos.get(i))
                new_struct_qualified_name = tuple_info.element_struct_qualified_names.get(i)
                new_anonymous_struct_info = self._copy_anonymous_struct_info(
                    tuple_info.element_anonymous_struct_infos.get(i)
                )
                if existing is None or existing.resolved_type != element_type:
                    new_sym = self.symbols.define(
                        id=var_name,
                        kind=SymbolKind.VARIABLE,
                        resolved_type=element_type,
                        interval=token.getSourceInterval(),
                        is_shadow=existing is not None,
                    )
                    new_sym.tuple_info = new_tuple_info
                    new_sym.callable_info = new_callable_info
                    new_sym.anonymous_struct_info = new_anonymous_struct_info
                    if new_struct_qualified_name is not None:
                        self._struct_symbol_bindings[new_sym.unique_name] = new_struct_qualified_name
                else:
                    existing.is_mutated = True
                    if new_tuple_info:
                        existing.tuple_info = new_tuple_info
                    if new_callable_info:
                        existing.callable_info = new_callable_info
                    existing.anonymous_struct_info = new_anonymous_struct_info
                    if new_struct_qualified_name is not None:
                        self._struct_symbol_bindings[existing.unique_name] = new_struct_qualified_name
                    temp = self.symbols.define_temp(
                        resolved_type=element_type,
                        interval=token.getSourceInterval(),
                    )
                    temp.tuple_info = new_tuple_info
                    temp.callable_info = new_callable_info
                    temp.anonymous_struct_info = self._copy_anonymous_struct_info(new_anonymous_struct_info)
                    if new_struct_qualified_name is not None:
                        self._struct_symbol_bindings[temp.unique_name] = new_struct_qualified_name
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
            return_exact_type = expr_symbol.exact_type if expr_symbol else self._resolved_exact_type(return_type, None)
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
            if return_type == BaseType.CALLABLE and expr_symbol:
                self._current_return_callable_info = self._merge_callable_info(
                    self._current_return_callable_info, expr_symbol.callable_info, "function return"
                )
            if return_type == BaseType.STRUCT and expr_symbol:
                expr_struct_qualified_name, expr_anonymous_struct_info = self._struct_metadata_for_symbol(expr_symbol)
                if self._current_return_struct_qualified_name is None and self._current_return_anonymous_struct_info is None:
                    self._current_return_struct_qualified_name = expr_struct_qualified_name
                    self._current_return_anonymous_struct_info = self._copy_anonymous_struct_info(
                        expr_anonymous_struct_info
                    )
                elif not self._structs_compatible(
                    self._current_return_struct_qualified_name,
                    self._current_return_anonymous_struct_info,
                    expr_struct_qualified_name,
                    expr_anonymous_struct_info,
                ):
                    raise ZincTypeError("function return paths use incompatible struct types")
            if self._current_return_type == BaseType.VOID:
                self._current_return_type = return_type
                self._current_return_exact_type = return_exact_type
            elif return_type != BaseType.UNKNOWN and return_type != self._current_return_type:
                # Promote int+float -> float when return paths disagree
                if {self._current_return_type, return_type} == {BaseType.INTEGER, BaseType.FLOAT}:
                    self._current_return_type = BaseType.FLOAT
                    self._current_return_exact_type = self._merge_exact_type_for_base(
                        self._current_return_exact_type,
                        return_exact_type,
                        self._current_return_type,
                        "function return paths",
                    )
                elif (
                    self._current_return_type == BaseType.CALLABLE
                    and return_type == BaseType.CALLABLE
                ):
                    pass
                else:
                    raise ZincTypeError("function return paths use incompatible types")
            elif self._current_return_exact_type is None:
                self._current_return_exact_type = return_exact_type
            else:
                self._current_return_exact_type = self._merge_exact_type_for_base(
                    self._current_return_exact_type,
                    return_exact_type,
                    self._current_return_type,
                    "function return paths",
                )

    def _define_match_field_binding(self, token, field: StructFieldInfo) -> None:
        """Define one binding introduced by an enum payload match pattern."""
        exact_type = field.exact_type or self._exact_type_name_from_text(field.type_annotation)
        symbol = self.symbols.define(
            id=token.getText(),
            kind=SymbolKind.VARIABLE,
            resolved_type=field.resolved_type,
            interval=token.getSourceInterval(),
            exact_type=exact_type,
            is_shadow=self.symbols.lookup_by_id(token.getText()) is not None,
        )
        if field.array_info is not None:
            symbol.element_type = field.array_info.element_type
            symbol.element_exact_type = field.array_info.element_exact_type
            symbol.tuple_info = self._copy_tuple_info(field.array_info.element_tuple_info)
            symbol.callable_info = self._copy_callable_info(field.array_info.element_callable_info)
            symbol.element_struct_qualified_name = field.array_info.element_struct_qualified_name
            symbol.element_anonymous_struct_info = self._copy_anonymous_struct_info(
                field.array_info.element_anonymous_struct_info
            )
        elif field.dict_info is not None:
            symbol.dict_info = self._copy_dict_info(field.dict_info)
        elif field.set_info is not None:
            symbol.set_info = self._copy_set_info(field.set_info)
        elif field.tuple_info is not None:
            symbol.tuple_info = self._copy_tuple_info(field.tuple_info)
        elif field.callable_info is not None:
            symbol.callable_info = self._copy_callable_info(field.callable_info)
        elif field.resolved_type == BaseType.STRUCT:
            symbol.anonymous_struct_info = self._copy_anonymous_struct_info(field.anonymous_struct_info)
            if field.struct_qualified_name is not None:
                self._struct_symbol_bindings[symbol.unique_name] = field.struct_qualified_name

    def visitMatchStatement(self, ctx: ZincParser.MatchStatementContext) -> None:
        """Visit a statement-form enum match."""
        scrutinee = self._value_info_from_expression(ctx.expression())
        if scrutinee.base_type != BaseType.ENUM or scrutinee.exact_type is None:
            raise ZincTypeError("match currently supports enum values only")
        if self._current_module is None:
            raise ZincTypeError("match requires a module context")

        enum_info = self._analyze_enum_by_qualified_name(scrutinee.exact_type)
        variant_map = {variant.name: variant for variant in enum_info.variants}
        covered_variants: set[str] = set()
        saw_wildcard = False
        arms = list(ctx.matchArm())

        for arm_index, arm_ctx in enumerate(arms):
            pattern_ctx = arm_ctx.pattern()
            is_wildcard = pattern_ctx.getText() == "_"
            variant: EnumVariantInfo | None = None
            variant_name: str | None = None
            field_patterns = []

            if is_wildcard:
                if saw_wildcard:
                    raise ZincTypeError("match supports at most one wildcard arm")
                if arm_index != len(arms) - 1:
                    raise ZincTypeError("wildcard match arm must be last")
                saw_wildcard = True
            else:
                enum_pattern = pattern_ctx.enumVariantPattern()
                if enum_pattern is None:
                    raise ZincTypeError("enum match arms must use enum variants or '_'")
                variant_target = self.module_graph.resolve_enum_variant_path(
                    self._current_module,
                    enum_pattern.enumVariantPath().getText().split("."),
                )
                if variant_target is None:
                    raise ZincTypeError(f"unknown enum variant '{enum_pattern.enumVariantPath().getText()}'")
                enum_symbol, variant_name = variant_target
                if enum_symbol.qualified_name != enum_info.qualified_name:
                    raise ZincTypeError(
                        f"match arm '{enum_pattern.enumVariantPath().getText()}' does not belong to enum '{enum_info.name}'"
                    )
                if variant_name in covered_variants:
                    raise ZincTypeError(f"duplicate match arm for variant '{enum_info.name}.{variant_name}'")
                covered_variants.add(variant_name)
                variant = variant_map.get(variant_name)
                if variant is None:
                    raise ZincTypeError(f"enum '{enum_info.name}' has no variant '{variant_name}'")
                field_patterns = list(enum_pattern.enumVariantFieldPattern())

            block_name = self._next_block_name("match")
            self.symbols.enter_scope(block_name)
            try:
                if variant is not None:
                    if variant.is_unit:
                        if field_patterns:
                            raise ZincTypeError(
                                f"unit variant '{enum_info.name}.{variant.name}' does not take fields in match patterns"
                            )
                    else:
                        if not field_patterns:
                            raise ZincTypeError(
                                f"payload variant '{enum_info.name}.{variant.name}' requires a field pattern"
                            )
                        seen_fields: set[str] = set()
                        seen_bindings: set[str] = set()
                        field_map = {field.name: field for field in variant.fields}
                        for field_pattern in field_patterns:
                            identifiers = list(field_pattern.IDENTIFIER())
                            field_name = identifiers[0].getText()
                            binding_token = identifiers[-1]
                            binding_name = binding_token.getText()
                            if field_name in seen_fields:
                                raise ZincTypeError(
                                    f"match pattern for variant '{enum_info.name}.{variant.name}' has duplicate field '{field_name}'"
                                )
                            if binding_name in seen_bindings:
                                raise ZincTypeError(
                                    f"match pattern for variant '{enum_info.name}.{variant.name}' reuses binding '{binding_name}'"
                                )
                            seen_fields.add(field_name)
                            seen_bindings.add(binding_name)
                            field = field_map.get(field_name)
                            if field is None:
                                raise ZincTypeError(
                                    f"variant '{enum_info.name}.{variant.name}' has no field '{field_name}'"
                                )
                            self._define_match_field_binding(binding_token, field)
                        missing_fields = [
                            field.name for field in variant.fields if field.name not in seen_fields
                        ]
                        if missing_fields:
                            raise ZincTypeError(
                                f"match pattern for variant '{enum_info.name}.{variant.name}' is missing field '{missing_fields[0]}'"
                            )

                if arm_ctx.block() is not None:
                    self.visit(arm_ctx.block())
                else:
                    self.visit(arm_ctx.expression())
            finally:
                self.symbols.exit_scope()

        if not saw_wildcard and len(covered_variants) != len(variant_map):
            missing_variant = next(
                variant.name for variant in enum_info.variants if variant.name not in covered_variants
            )
            raise ZincTypeError(
                f"non-exhaustive match for enum '{enum_info.name}'; missing variant '{missing_variant}'"
            )

    def visitIfExpr(self, ctx: ZincParser.IfExprContext) -> BaseType:
        """Visit an if-expression wrapper."""
        return self.visit(ctx.ifExpression())

    def visitIfExpression(self, ctx: ZincParser.IfExpressionContext) -> BaseType:
        """Visit an if-expression and resolve its merged result type."""
        value_info = self._analyze_if_expression_ctx(ctx)
        self._record_value_info(ctx.getSourceInterval(), value_info)
        return value_info.base_type

    def visitIfStatement(self, ctx: ZincParser.IfStatementContext) -> None:
        """Visit if/else statement."""
        for expr in ctx.expression():
            self._require_boolean_condition(expr, "if condition")

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
        self._loop_depth += 1

        binding = ctx.forBinding()
        binding_ctx = binding.tupleAssignmentTarget() or binding
        tokens = self._binding_tokens(binding_ctx)

        def define_binding(
            index: int,
            resolved_type: BaseType,
            exact_type: str | None = None,
            tuple_info: TupleTypeInfo | None = None,
            callable_info: CallableTypeInfo | None = None,
            struct_qualified_name: str | None = None,
            anonymous_struct_info: AnonymousStructTypeInfo | None = None,
        ) -> None:
            token = tokens[index]
            symbol = self.symbols.define(
                id=token.getText(),
                kind=SymbolKind.VARIABLE,
                resolved_type=resolved_type,
                interval=token.getSourceInterval(),
                exact_type=exact_type,
            )
            symbol.tuple_info = self._copy_tuple_info(tuple_info)
            symbol.callable_info = self._copy_callable_info(callable_info)
            symbol.anonymous_struct_info = self._copy_anonymous_struct_info(anonymous_struct_info)
            if struct_qualified_name is not None:
                self._struct_symbol_bindings[symbol.unique_name] = struct_qualified_name

        item_tuple_info: TupleTypeInfo | None = None
        item_callable_info: CallableTypeInfo | None = None
        item_exact_type: str | None = None
        item_struct_qualified_name: str | None = None
        item_anonymous_struct_info: AnonymousStructTypeInfo | None = None
        if iterable_type == BaseType.INTEGER:
            var_type = BaseType.INTEGER
        elif iterable_type == BaseType.ARRAY:
            var_type = BaseType.UNKNOWN
            if expr_symbol and expr_symbol.element_type:
                var_type = expr_symbol.element_type
                item_exact_type = expr_symbol.element_exact_type
                if var_type == BaseType.TUPLE:
                    item_tuple_info = expr_symbol.tuple_info
                if var_type == BaseType.CALLABLE:
                    item_callable_info = expr_symbol.callable_info
                if var_type == BaseType.STRUCT:
                    item_struct_qualified_name = expr_symbol.element_struct_qualified_name
                    item_anonymous_struct_info = expr_symbol.element_anonymous_struct_info
        elif iterable_type == BaseType.SET:
            var_type = BaseType.UNKNOWN
            if expr_symbol and expr_symbol.set_info:
                var_type = expr_symbol.set_info.element_type
                item_exact_type = expr_symbol.set_info.element_exact_type
                if var_type == BaseType.STRUCT:
                    item_struct_qualified_name = expr_symbol.set_info.element_struct_qualified_name
                    item_anonymous_struct_info = expr_symbol.set_info.element_anonymous_struct_info
        elif iterable_type == BaseType.DICT:
            var_type = BaseType.TUPLE
            if expr_symbol and expr_symbol.dict_info:
                item_tuple_info = self._tuple_info_from_dict_info(expr_symbol.dict_info)
        elif iterable_type == BaseType.CHANNEL:
            chan_info = self._channel_info_for_expr(ctx.expression())
            var_type = BaseType.UNKNOWN
            if chan_info is not None:
                var_type = chan_info.element_type
                item_exact_type = chan_info.element_exact_type
                if var_type == BaseType.TUPLE:
                    item_tuple_info = chan_info.element_tuple_info
                if var_type == BaseType.CALLABLE:
                    item_callable_info = chan_info.element_callable_info
                if var_type == BaseType.STRUCT:
                    item_struct_qualified_name = chan_info.element_struct_qualified_name
                    item_anonymous_struct_info = chan_info.element_anonymous_struct_info
        else:
            var_type = BaseType.UNKNOWN

        if len(tokens) == 1:
            define_binding(
                0,
                var_type,
                item_exact_type,
                item_tuple_info,
                item_callable_info,
                item_struct_qualified_name,
                item_anonymous_struct_info,
            )
        else:
            if var_type != BaseType.TUPLE or item_tuple_info is None:
                raise ZincTypeError("for-loop destructuring requires tuple items")
            if len(tokens) != len(item_tuple_info.element_types):
                raise ZincTypeError("for-loop destructuring arity mismatch")
            for i, element_type in enumerate(item_tuple_info.element_types):
                define_binding(
                    i,
                    element_type,
                    item_tuple_info.element_exact_types[i] if i < len(item_tuple_info.element_exact_types) else None,
                    item_tuple_info.element_tuple_infos.get(i),
                    item_tuple_info.element_callable_infos.get(i),
                    item_tuple_info.element_struct_qualified_names.get(i),
                    item_tuple_info.element_anonymous_struct_infos.get(i),
                )

        iterated_dict_name = self._iterated_dict_name(ctx.expression())
        self._iterating_dict_stack.append({iterated_dict_name} if iterated_dict_name else set())
        try:
            self.visit(ctx.block())
        finally:
            self._iterating_dict_stack.pop()
            self._loop_depth -= 1
            self.symbols.exit_scope()

    def visitWhileStatement(self, ctx: ZincParser.WhileStatementContext) -> None:
        """Visit while loop statement."""
        self.visit(ctx.expression())

        block_name = self._next_block_name("while")
        self.symbols.enter_scope(block_name)
        self._loop_depth += 1
        try:
            self.visit(ctx.block())
        finally:
            self._loop_depth -= 1
            self.symbols.exit_scope()

    def visitLoopStatement(self, ctx: ZincParser.LoopStatementContext) -> None:
        """Visit loop statement."""
        block_name = self._next_block_name("loop")
        self.symbols.enter_scope(block_name)
        self._loop_depth += 1
        try:
            self.visit(ctx.block())
        finally:
            self._loop_depth -= 1
            self.symbols.exit_scope()

    def visitFunctionDeclaration(self, ctx: ZincParser.FunctionDeclarationContext) -> None:
        """Finalize a nested sync function declaration without visiting its body here."""
        info = self._current_lexical_function(ctx.IDENTIFIER().getText())
        if info is None:
            info = self._register_lexical_function_stub(
                ctx.IDENTIFIER().getText(),
                ctx,
                is_async=False,
                display_name=ctx.IDENTIFIER().getText(),
            )
        self._analyze_lexical_captures(info)

    def visitAsyncFunctionDeclaration(self, ctx: ZincParser.AsyncFunctionDeclarationContext) -> None:
        """Finalize a nested async function declaration without visiting its body here."""
        info = self._current_lexical_function(ctx.IDENTIFIER().getText())
        if info is None:
            info = self._register_lexical_function_stub(
                ctx.IDENTIFIER().getText(),
                ctx,
                is_async=True,
                display_name=ctx.IDENTIFIER().getText(),
            )
        self._analyze_lexical_captures(info)

    def visitBlock(self, ctx: ZincParser.BlockContext) -> None:
        """Visit a block of statements."""
        self._visit_block_statements(ctx, as_value=False)

    def visitExpressionStatement(self, ctx: ZincParser.ExpressionStatementContext) -> None:
        """Visit expression statement."""
        self.visit(ctx.expression())

    def visitBreakStatement(self, ctx: ZincParser.BreakStatementContext) -> None:
        """Visit break and ensure it appears inside a loop."""
        if self._loop_depth == 0:
            raise ZincTypeError("break is only valid inside a loop")

    def visitContinueStatement(self, ctx: ZincParser.ContinueStatementContext) -> None:
        """Visit continue and ensure it appears inside a loop."""
        if self._loop_depth == 0:
            raise ZincTypeError("continue is only valid inside a loop")

    def visitSuperAssignment(self, ctx: ZincParser.SuperAssignmentContext) -> None:
        """Visit closure super-assignment to a captured outer binding."""
        name = ctx.IDENTIFIER().getText()
        symbol = self.symbols.lookup_by_id(name)
        if symbol is None or not symbol.is_captured_ref:
            raise ZincTypeError(f"'<<-' expects a captured outer variable '{name}'")
        expr_type = self.visit(ctx.expression())
        expr_symbol = self._expr_symbol(ctx.expression())
        if not self._assignment_metadata_compatible(
            symbol.resolved_type,
            expr_type,
            expected_dict=symbol.dict_info,
            actual_dict=self._copy_dict_info(expr_symbol.dict_info) if expr_symbol else None,
            expected_set=symbol.set_info,
            actual_set=self._copy_set_info(expr_symbol.set_info) if expr_symbol else None,
            expected_tuple=symbol.tuple_info,
            actual_tuple=self._copy_tuple_info(expr_symbol.tuple_info) if expr_symbol else None,
            expected_callable=symbol.callable_info,
            actual_callable=self._copy_callable_info(expr_symbol.callable_info) if expr_symbol else None,
            expected_struct_qualified_name=self._struct_qualified_name_for_symbol(symbol),
            actual_struct_qualified_name=self._struct_qualified_name_for_symbol(expr_symbol),
            expected_anonymous_struct_info=symbol.anonymous_struct_info,
            actual_anonymous_struct_info=self._copy_anonymous_struct_info(
                expr_symbol.anonymous_struct_info if expr_symbol else None
            ),
        ):
            raise ZincTypeError(f"captured outer variable '{name}' cannot change type after capture")
        symbol.is_mutated = True
        self.symbols.define_temp(
            resolved_type=symbol.resolved_type,
            interval=ctx.getSourceInterval(),
        )

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
        channel_expr = ctx.expression()
        channel_type = self.visit(channel_expr)
        if channel_type != BaseType.CHANNEL:
            raise ZincTypeError("select receive expects a channel expression")
        channel_info = self._channel_info_ref_for_expr(channel_expr)
        if channel_info is None:
            channel_info = ChannelTypeInfo(element_type=BaseType.UNKNOWN)
        if (
            binding_ctx := ctx.selectReceiveBinding()
        ) is not None and binding_ctx.tupleAssignmentTarget() is not None and channel_info.element_type == BaseType.ENUM:
            raise ZincTypeError("close-aware select receive is not supported for enum channels in v1")

        block_name = self._next_block_name("select")
        self.symbols.enter_scope(block_name)
        try:
            binding_ctx = ctx.selectReceiveBinding()
            if binding_ctx is not None:
                if binding_ctx.IDENTIFIER():
                    binding_name = binding_ctx.IDENTIFIER().getText()
                    binding_symbol = self.symbols.define(
                        id=binding_name,
                        kind=SymbolKind.VARIABLE,
                        resolved_type=channel_info.element_type,
                        interval=binding_ctx.IDENTIFIER().getSourceInterval(),
                        exact_type=channel_info.element_exact_type,
                        is_shadow=self.symbols.lookup_by_id(binding_name) is not None,
                    )
                    binding_symbol.tuple_info = self._copy_tuple_info(channel_info.element_tuple_info)
                    if channel_info.element_type == BaseType.CALLABLE:
                        binding_symbol.callable_info = channel_info.element_callable_info
                    if channel_info.element_type == BaseType.STRUCT:
                        binding_symbol.anonymous_struct_info = self._copy_anonymous_struct_info(
                            channel_info.element_anonymous_struct_info
                        )
                        if channel_info.element_struct_qualified_name is not None:
                            self._struct_symbol_bindings[binding_symbol.unique_name] = (
                                channel_info.element_struct_qualified_name
                            )
                else:
                    tokens = self._binding_tokens(binding_ctx.tupleAssignmentTarget())
                    if len(tokens) != 2:
                        raise ZincTypeError("close-aware select receive requires exactly two bindings")
                    binding_types = [channel_info.element_type, BaseType.BOOLEAN]
                    binding_exact_types = [channel_info.element_exact_type, default_exact_type(BaseType.BOOLEAN)]
                    binding_tuple_infos = [self._copy_tuple_info(channel_info.element_tuple_info), None]
                    binding_callable_infos = [channel_info.element_callable_info, None]
                    binding_struct_names = [channel_info.element_struct_qualified_name, None]
                    binding_anonymous_struct_infos = [
                        self._copy_anonymous_struct_info(channel_info.element_anonymous_struct_info),
                        None,
                    ]
                    for i, token in enumerate(tokens):
                        binding_symbol = self.symbols.define(
                            id=token.getText(),
                            kind=SymbolKind.VARIABLE,
                            resolved_type=binding_types[i],
                            interval=token.getSourceInterval(),
                            exact_type=binding_exact_types[i],
                            is_shadow=self.symbols.lookup_by_id(token.getText()) is not None,
                        )
                        binding_symbol.tuple_info = binding_tuple_infos[i]
                        binding_symbol.callable_info = binding_callable_infos[i]
                        binding_symbol.anonymous_struct_info = binding_anonymous_struct_infos[i]
                        if binding_struct_names[i] is not None:
                            self._struct_symbol_bindings[binding_symbol.unique_name] = binding_struct_names[i]
            self.visit(ctx.block())
        finally:
            self.symbols.exit_scope()

    def visitSelectSendCase(self, ctx: ZincParser.SelectSendCaseContext) -> None:
        """Visit a select send case."""
        channel_name = ctx.IDENTIFIER().getText()
        value_type = self.visit(ctx.expression())
        value_symbol = self._expr_symbol(ctx.expression())
        value_callable_info = value_symbol.callable_info if value_symbol else None
        value_struct_qualified_name, value_anonymous_struct_info = self._struct_metadata_for_symbol(value_symbol)
        if value_type == BaseType.CALLABLE:
            self._validate_channel_callable_send(value_callable_info)
        self._merge_channel_value_type(
            channel_name,
            value_type,
            value_symbol.exact_type if value_symbol else None,
            value_callable_info,
            value_struct_qualified_name,
            value_anonymous_struct_info,
        )

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

        # Collect argument types and track channel arguments
        arg_types: list[BaseType] = []
        arg_exact_types: list[str | None] = []
        arg_exprs = list(ctx.argumentList().expression()) if ctx.argumentList() else []
        arg_channel_infos: dict[int, ChannelTypeInfo] = {}
        arg_callable_infos: dict[int, CallableTypeInfo] = {}
        arg_struct_qualified_names: dict[int, str] = {}
        arg_anonymous_struct_infos: dict[int, AnonymousStructTypeInfo] = {}
        if ctx.argumentList():
            for i, arg_expr in enumerate(arg_exprs):
                arg_type = self.visit(arg_expr)
                arg_types.append(arg_type)
                arg_symbol = self._expr_symbol(arg_expr)
                arg_exact_types.append(
                    arg_symbol.exact_type if arg_symbol else self._resolved_exact_type(arg_type, None)
                )

                if arg_type == BaseType.CHANNEL:
                    if isinstance(arg_expr, ZincParser.PrimaryExprContext):
                        arg_primary = arg_expr.primaryExpression()
                        if arg_primary and arg_primary.IDENTIFIER():
                            chan_var = arg_primary.IDENTIFIER().getText()
                            if chan_var in self._channel_infos:
                                arg_channel_infos[i] = self._channel_infos[chan_var]
                                continue
                    arg_symbol = self._expr_symbol(arg_expr)
                    if arg_symbol and arg_symbol.channel_info:
                        arg_channel_infos[i] = self._copy_channel_info(arg_symbol.channel_info) or ChannelTypeInfo()
                elif arg_type == BaseType.CALLABLE:
                    arg_symbol = self._expr_symbol(arg_expr)
                    if arg_symbol and arg_symbol.callable_info:
                        arg_callable_infos[i] = self._copy_callable_info(arg_symbol.callable_info) or CallableTypeInfo()
                elif arg_type == BaseType.STRUCT:
                    arg_symbol = self._expr_symbol(arg_expr)
                    if arg_symbol:
                        struct_qualified_name, anonymous_struct_info = self._struct_metadata_for_symbol(arg_symbol)
                        if struct_qualified_name is not None:
                            arg_struct_qualified_names[i] = struct_qualified_name
                        if anonymous_struct_info is not None:
                            arg_anonymous_struct_infos[i] = self._copy_anonymous_struct_info(
                                anonymous_struct_info
                            ) or AnonymousStructTypeInfo()

        if path and len(path) == 1:
            lexical_function = self._current_lexical_function(path[0])
            if lexical_function is not None and BaseType.UNKNOWN not in arg_types:
                self._validate_annotated_parameters(
                    lexical_function.ctx,
                    arg_types,
                    arg_exact_types,
                    arg_exprs,
                    {},
                    {},
                    {},
                    {},
                    arg_callable_infos,
                    arg_struct_qualified_names,
                    arg_anonymous_struct_infos,
                )
                mangled = self.atlas.add_specialization(
                    lexical_function.qualified_name,
                    arg_types,
                    arg_exact_types,
                    lexical_function.ctx,
                    self._current_function,
                    arg_channel_infos,
                    arg_callable_infos=arg_callable_infos,
                    arg_struct_qualified_names=arg_struct_qualified_names,
                    arg_anonymous_struct_infos=arg_anonymous_struct_infos,
                )
                key = (self._current_function, ctx.getSourceInterval())
                self.specialization_map[key] = mangled
                self.atlas.functions[mangled].is_async = lexical_function.is_async
                for idx, chan_info in arg_channel_infos.items():
                    self.atlas.functions[mangled].arg_channel_infos.setdefault(idx, [])
                    if all(
                        existing is not chan_info
                        for existing in self.atlas.functions[mangled].arg_channel_infos[idx]
                    ):
                        self.atlas.functions[mangled].arg_channel_infos[idx].append(chan_info)
                return

        if path is not None and self._current_module is not None:
            resolved_function = self.module_graph.resolve_function_path(self._current_module, path)
            if resolved_function is not None and resolved_function.name not in ("print", "chan"):
                func_def = self.atlas.function_defs.get(resolved_function.qualified_name)
                if func_def is not None and BaseType.UNKNOWN not in arg_types:
                    self._validate_annotated_parameters(
                        func_def,
                        arg_types,
                        arg_exact_types,
                        arg_exprs,
                        {},
                        {},
                        {},
                        {},
                        arg_callable_infos,
                        arg_struct_qualified_names,
                        arg_anonymous_struct_infos,
                    )
                    mangled = self.atlas.add_specialization(
                        resolved_function.qualified_name,
                        arg_types,
                        arg_exact_types,
                        func_def,
                        self._current_function,
                        arg_channel_infos,
                        arg_callable_infos=arg_callable_infos,
                        arg_struct_qualified_names=arg_struct_qualified_names,
                        arg_anonymous_struct_infos=arg_anonymous_struct_infos,
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
                    return

        callee_type = self.visit(func_expr)
        callee_symbol = self._expr_symbol(func_expr)
        if callee_type == BaseType.CALLABLE and callee_symbol and callee_symbol.callable_info:
            if not self._callable_is_transport_safe(callee_symbol.callable_info):
                raise ZincTypeError("closure captures are not transport-safe for spawn")
            return

    def visitChannelSendStatement(self, ctx: ZincParser.ChannelSendStatementContext) -> None:
        """Visit channel send statement and infer channel element type."""
        channel_name = ctx.IDENTIFIER().getText()
        value_type = self.visit(ctx.expression())
        value_symbol = self._expr_symbol(ctx.expression())
        value_callable_info = value_symbol.callable_info if value_symbol else None
        value_struct_qualified_name, value_anonymous_struct_info = self._struct_metadata_for_symbol(value_symbol)
        if value_type == BaseType.CALLABLE:
            self._validate_channel_callable_send(value_callable_info)
        self._merge_channel_value_type(
            channel_name,
            value_type,
            value_symbol.exact_type if value_symbol else None,
            value_callable_info,
            value_struct_qualified_name,
            value_anonymous_struct_info,
        )

    def visitChannelReceiveExpr(self, ctx: ZincParser.ChannelReceiveExprContext) -> BaseType:
        """Visit channel receive expression."""
        chan_expr = ctx.expression()
        expr_type = self.visit(chan_expr)

        if expr_type != BaseType.CHANNEL:
            raise ZincTypeError("channel receive expects a channel expression")

        channel_info = self._channel_info_ref_for_expr(chan_expr)
        elem_type = channel_info.element_type if channel_info is not None else BaseType.UNKNOWN
        temp = self.symbols.define_temp(
            resolved_type=elem_type,
            interval=ctx.getSourceInterval(),
            exact_type=channel_info.element_exact_type if channel_info is not None else None,
        )
        if channel_info is not None:
            temp.tuple_info = self._copy_tuple_info(channel_info.element_tuple_info)
            temp.callable_info = channel_info.element_callable_info
            temp.anonymous_struct_info = self._copy_anonymous_struct_info(
                channel_info.element_anonymous_struct_info
            )
            if channel_info.element_struct_qualified_name is not None:
                self._struct_symbol_bindings[temp.unique_name] = channel_info.element_struct_qualified_name
        return elem_type
