"""Atlas - Graph of all code reachable from the entry module's main()."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from antlr4 import ParserRuleContext
from sortedcontainers import SortedDict, SortedSet

from zinc.ast.types import (
    ArrayTypeInfo,
    BaseType,
    CallableTypeInfo,
    ChannelTypeInfo,
    DictTypeInfo,
    SetTypeInfo,
    TupleTypeInfo,
    type_to_rust,
)
from zinc.modules import (
    ModuleGraph,
    extract_identifier_path,
    struct_composition_from_ctx,
    struct_path_from_ctx,
)
from zinc.parser.zincParser import zincParser as ZincParser

CompositionMode = str


@dataclass
class FunctionInstance:
    """A specific instantiation of a function (possibly monomorphized)."""

    name: str  # Unqualified function name
    qualified_name: str  # Canonical id like "foo/bar::add"
    module_id: str
    mangled_name: str  # Unique Rust name
    ctx: ParserRuleContext  # Parse tree reference
    arg_types: list[BaseType]  # Concrete argument types
    return_type: BaseType = field(default=BaseType.VOID)  # Inferred return type
    is_async: bool = False  # True if called via spawn (becomes async fn)
    # Rich type info for channel arguments (arg_index -> list of ChannelTypeInfos from all call sites)
    arg_channel_infos: dict[int, list[ChannelTypeInfo]] = field(default_factory=dict)
    # Rich type info for array arguments (arg_index -> ArrayTypeInfo)
    arg_array_infos: dict[int, ArrayTypeInfo] = field(default_factory=dict)
    # Rich type info for dict arguments (arg_index -> DictTypeInfo)
    arg_dict_infos: dict[int, DictTypeInfo] = field(default_factory=dict)
    # Rich type info for set arguments (arg_index -> SetTypeInfo)
    arg_set_infos: dict[int, SetTypeInfo] = field(default_factory=dict)
    # Rich type info for tuple arguments (arg_index -> TupleTypeInfo)
    arg_tuple_infos: dict[int, TupleTypeInfo] = field(default_factory=dict)
    # Rich type info for callable arguments (arg_index -> CallableTypeInfo)
    arg_callable_infos: dict[int, CallableTypeInfo] = field(default_factory=dict)
    # Rich type info for collection return values
    return_dict_info: DictTypeInfo | None = None
    return_set_info: SetTypeInfo | None = None
    return_tuple_info: TupleTypeInfo | None = None
    return_callable_info: CallableTypeInfo | None = None


@dataclass
class StructFieldInfo:
    """Analyzed struct field information."""

    name: str
    type_annotation: str | None = None
    default_value: str | None = None
    is_private: bool = False
    is_const: bool = False
    resolved_type: BaseType = field(default=BaseType.UNKNOWN)
    callable_info: CallableTypeInfo | None = None
    source_struct_qualified_name: str | None = None

    def rust_type(self) -> str:
        """Get Rust type string for this field."""
        if self.callable_info is not None:
            return self.callable_info.rust_type_name()
        if self.type_annotation:
            mapping = {
                "i8": "i8",
                "i16": "i16",
                "i32": "i32",
                "i64": "i64",
                "i128": "i128",
                "u8": "u8",
                "u16": "u16",
                "u32": "u32",
                "u64": "u64",
                "u128": "u128",
                "f8": "f8",
                "f16": "f16",
                "f32": "f32",
                "f64": "f64",
                "f128": "f128",
                "string": "String",
                "bool": "bool",
            }
            return mapping.get(self.type_annotation.lower(), self.type_annotation)
        return type_to_rust(self.resolved_type)

    def rust_default(self) -> str:
        """Get Rust default value for this field."""
        if self.default_value:
            if self.rust_type() == "String" and self.default_value.startswith('"'):
                return f"String::from({self.default_value})"
            return self.default_value
        defaults = {
            "i8": "0",
            "i16": "0",
            "i32": "0",
            "i64": "0",
            "i128": "0",
            "u8": "0",
            "u16": "0",
            "u32": "0",
            "u64": "0",
            "u128": "0",
            "f8": "0.0",
            "f16": "0.0",
            "f32": "0.0",
            "f64": "0.0",
            "f128": "0.0",
            "String": "String::new()",
            "bool": "false",
        }
        return defaults.get(self.rust_type(), "Default::default()")


@dataclass
class StructMethodInfo:
    """Analyzed struct method information."""

    name: str
    parameters: list[tuple[str, str | None, str | None]] = field(default_factory=list)
    is_static: bool = False
    self_mutability: str | None = None
    return_type: str | None = None
    body_ctx: ParserRuleContext | None = None
    source_struct_qualified_name: str | None = None
    source_module_id: str | None = None
    constructor_owner_qualified_name: str | None = None


@dataclass
class StructInstance:
    """A struct that is used in the program."""

    name: str
    qualified_name: str
    module_id: str
    ctx: ParserRuleContext
    methods_used: SortedSet[str] = field(default_factory=SortedSet)
    fields: list[StructFieldInfo] = field(default_factory=list)
    methods: list[StructMethodInfo] = field(default_factory=list)
    composition_mode: CompositionMode | None = None
    composition_sources: tuple[str, ...] = ()


@dataclass
class ConstInstance:
    """A global constant declaration."""

    name: str
    qualified_name: str
    module_id: str
    ctx: ParserRuleContext


@dataclass
class Atlas:
    """Graph of all code reachable from main()."""

    module_graph: ModuleGraph
    main: FunctionInstance
    functions: SortedDict[str, FunctionInstance] = field(default_factory=SortedDict)
    structs: SortedDict[str, StructInstance] = field(default_factory=SortedDict)
    consts: SortedDict[str, ConstInstance] = field(default_factory=SortedDict)
    calls: SortedDict[str, SortedSet[str]] = field(default_factory=SortedDict)
    struct_usages: SortedDict[str, SortedSet[str]] = field(default_factory=SortedDict)
    const_usages: SortedDict[str, SortedSet[str]] = field(default_factory=SortedDict)
    function_defs: SortedDict[str, ParserRuleContext] = field(default_factory=SortedDict)

    def is_reachable(self, name: str) -> bool:
        """Check if a function, struct, or const is reachable."""
        return name in self.functions or name in self.structs or name in self.consts

    def add_specialization(
        self,
        qualified_name: str,
        arg_types: list[BaseType],
        ctx: ParserRuleContext,
        caller_mangled: str | None = None,
        arg_channel_infos: dict[int, ChannelTypeInfo] | None = None,
        arg_array_infos: dict[int, ArrayTypeInfo] | None = None,
        arg_dict_infos: dict[int, DictTypeInfo] | None = None,
        arg_set_infos: dict[int, SetTypeInfo] | None = None,
        arg_tuple_infos: dict[int, TupleTypeInfo] | None = None,
        arg_callable_infos: dict[int, CallableTypeInfo] | None = None,
    ) -> str:
        """Create a new function specialization and return its mangled name."""
        mangled = self._mangle_name(
            qualified_name,
            arg_types,
            arg_channel_infos,
            arg_array_infos,
            arg_dict_infos,
            arg_set_infos,
            arg_tuple_infos,
            arg_callable_infos,
        )
        if mangled not in self.functions:
            module_id, name = ModuleGraph.split_qualified_name(qualified_name)
            self.functions[mangled] = FunctionInstance(
                name=name,
                qualified_name=qualified_name,
                module_id=module_id,
                mangled_name=mangled,
                ctx=ctx,
                arg_types=list(arg_types),
                arg_channel_infos={
                    index: [info]
                    for index, info in (arg_channel_infos or {}).items()
                },
                arg_array_infos=arg_array_infos or {},
                arg_dict_infos=arg_dict_infos or {},
                arg_set_infos=arg_set_infos or {},
                arg_tuple_infos=arg_tuple_infos or {},
                arg_callable_infos={
                    index: info.copy() for index, info in (arg_callable_infos or {}).items()
                },
            )
            self.calls[mangled] = SortedSet()
        elif arg_callable_infos:
            instance = self.functions[mangled]
            for index, info in arg_callable_infos.items():
                existing = instance.arg_callable_infos.get(index)
                if existing is None:
                    instance.arg_callable_infos[index] = info.copy()
                else:
                    try:
                        instance.arg_callable_infos[index] = existing.merge_targets_from(info)
                    except ValueError:
                        def specificity(callable_info: CallableTypeInfo) -> int:
                            unknowns = sum(
                                1 for base_type in callable_info.param_types if base_type == BaseType.UNKNOWN
                            )
                            if callable_info.return_type == BaseType.UNKNOWN:
                                unknowns += 1
                            return unknowns

                        chosen = existing if specificity(existing) <= specificity(info) else info
                        instance.arg_callable_infos[index] = chosen.copy()

        if caller_mangled and caller_mangled in self.calls:
            self.calls[caller_mangled].add(mangled)

        return mangled

    def _mangle_name(
        self,
        qualified_name: str,
        arg_types: list[BaseType],
        arg_channel_infos: dict[int, ChannelTypeInfo] | None = None,
        arg_array_infos: dict[int, ArrayTypeInfo] | None = None,
        arg_dict_infos: dict[int, DictTypeInfo] | None = None,
        arg_set_infos: dict[int, SetTypeInfo] | None = None,
        arg_tuple_infos: dict[int, TupleTypeInfo] | None = None,
        arg_callable_infos: dict[int, CallableTypeInfo] | None = None,
    ) -> str:
        """Generate a flattened Rust symbol name."""
        base_name = self.module_graph.rust_base_name(qualified_name)
        if not arg_types:
            return base_name

        type_parts = []
        for i, base_type in enumerate(arg_types):
            if base_type == BaseType.CHANNEL and arg_channel_infos and i in arg_channel_infos:
                type_parts.append(arg_channel_infos[i].to_rust_type_suffix())
            elif base_type == BaseType.ARRAY and arg_array_infos and i in arg_array_infos:
                type_parts.append(arg_array_infos[i].to_rust_type_suffix())
            elif base_type == BaseType.DICT and arg_dict_infos and i in arg_dict_infos:
                type_parts.append(arg_dict_infos[i].to_rust_type_suffix())
            elif base_type == BaseType.SET and arg_set_infos and i in arg_set_infos:
                type_parts.append(arg_set_infos[i].to_rust_type_suffix())
            elif base_type == BaseType.TUPLE and arg_tuple_infos and i in arg_tuple_infos:
                type_parts.append(arg_tuple_infos[i].to_rust_type_suffix())
            elif base_type == BaseType.CALLABLE and arg_callable_infos and i in arg_callable_infos:
                type_parts.append(arg_callable_infos[i].to_rust_type_suffix())
            else:
                type_parts.append(type_to_rust(base_type))

        return f"{base_name}_{'_'.join(type_parts)}"

    def topological_order(self) -> list[str]:
        """Return function mangled names in dependency order."""
        visited: set[str] = set()
        result: list[str] = []

        def dfs(name: str) -> None:
            if name in visited or name not in self.functions:
                return
            visited.add(name)
            for callee in self.calls.get(name, set()):
                if callee in self.functions:
                    dfs(callee)
            result.append(name)

        for name in self.functions:
            dfs(name)

        return result


class AtlasBuilder:
    """Build the Atlas from a module graph."""

    BUILTIN_FUNCTIONS = {"print", "chan", "dict", "sort_dict", "set", "sort_set"}

    def __init__(self, module_graph: ModuleGraph):
        self.module_graph = module_graph
        self._function_defs: SortedDict[str, ParserRuleContext] = SortedDict(
            self.module_graph.top_level_functions()
        )
        self._struct_defs: SortedDict[str, StructInstance] = SortedDict()
        self._const_defs: SortedDict[str, ConstInstance] = SortedDict()
        for symbol in self.module_graph.top_level_symbols.values():
            if symbol.kind == "struct":
                self._struct_defs[symbol.qualified_name] = StructInstance(
                    name=symbol.name,
                    qualified_name=symbol.qualified_name,
                    module_id=symbol.module_id,
                    ctx=symbol.ctx,
                )
            elif symbol.kind == "const":
                self._const_defs[symbol.qualified_name] = ConstInstance(
                    name=symbol.name,
                    qualified_name=symbol.qualified_name,
                    module_id=symbol.module_id,
                    ctx=symbol.ctx,
                )

        self._reachable_functions: SortedDict[str, FunctionInstance] = SortedDict()
        self._reachable_structs: SortedDict[str, StructInstance] = SortedDict()
        self._reachable_consts: SortedDict[str, ConstInstance] = SortedDict()
        self._calls: SortedDict[str, SortedSet[str]] = SortedDict()
        self._struct_usages: SortedDict[str, SortedSet[str]] = SortedDict()
        self._const_usages: SortedDict[str, SortedSet[str]] = SortedDict()
        self._current_function: str | None = None
        self._current_module: str | None = None

    def build(self) -> Atlas:
        """Build the Atlas after loading the full module graph."""
        entry_module = self.module_graph.get_module(self.module_graph.entry_module_id)
        main_symbol = entry_module.symbols.get("main")
        if main_symbol is None or main_symbol.kind != "function":
            raise ValueError("No main() function found")

        atlas = Atlas(
            module_graph=self.module_graph,
            main=FunctionInstance(
                name=main_symbol.name,
                qualified_name=main_symbol.qualified_name,
                module_id=main_symbol.module_id,
                mangled_name=self.module_graph.rust_base_name(main_symbol.qualified_name),
                ctx=main_symbol.ctx,
                arg_types=[],
            ),
            function_defs=self._function_defs,
        )
        self._reachable_functions[atlas.main.mangled_name] = atlas.main

        worklist = [main_symbol.qualified_name]
        visited: set[str] = set()

        while worklist:
            qualified_name = worklist.pop()
            if qualified_name in visited:
                continue
            visited.add(qualified_name)

            func_ctx = self._function_defs.get(qualified_name)
            if func_ctx is None:
                continue

            module_id, _ = ModuleGraph.split_qualified_name(qualified_name)
            caller_key = (
                atlas.main.mangled_name
                if qualified_name == atlas.main.qualified_name
                else qualified_name
            )
            self._current_function = caller_key
            self._current_module = module_id
            self._calls[caller_key] = SortedSet()
            self._struct_usages[caller_key] = SortedSet()
            self._const_usages[caller_key] = SortedSet()
            self._walk_for_references(func_ctx)

            for callee in self._calls[caller_key]:
                if callee in self._function_defs and callee not in visited:
                    worklist.append(callee)

        atlas.functions = self._reachable_functions
        atlas.structs = self._reachable_structs
        atlas.consts = self._reachable_consts
        atlas.calls = self._calls
        atlas.struct_usages = self._struct_usages
        atlas.const_usages = self._const_usages
        return atlas

    def _walk_for_references(self, ctx: ParserRuleContext) -> None:
        """Walk a parse tree node to find top-level references."""
        if ctx is None or self._current_function is None or self._current_module is None:
            return

        if isinstance(ctx, ZincParser.PrimaryExpressionContext) and ctx.IDENTIFIER():
            symbol = self.module_graph.resolve_const_path(
                self._current_module, [ctx.IDENTIFIER().getText()]
            )
            if symbol:
                self._add_const_usage(symbol.qualified_name)

        if isinstance(ctx, ZincParser.LiteralContext) and ctx.STRING():
            text = ctx.STRING().getText()[1:-1]
            for expr in re.findall(r"\{([^}]+)\}", text):
                for token in re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*\b", expr):
                    path = token.split(".")
                    const_symbol = self.module_graph.resolve_const_path(self._current_module, path)
                    if const_symbol:
                        self._add_const_usage(const_symbol.qualified_name)

        if isinstance(ctx, ZincParser.MemberAccessExprContext):
            path = extract_identifier_path(ctx)
            if path:
                const_symbol = self.module_graph.resolve_const_path(self._current_module, path)
                if const_symbol:
                    self._add_const_usage(const_symbol.qualified_name)
                static_target = self.module_graph.resolve_static_method_target(
                    self._current_module, path
                )
                if static_target:
                    struct_symbol, method_name = static_target
                    self._add_struct_usage(struct_symbol.qualified_name, method_name)

        if isinstance(ctx, ZincParser.FunctionCallExprContext):
            path = extract_identifier_path(ctx.expression())
            if path:
                func_symbol = self.module_graph.resolve_function_path(self._current_module, path)
                if func_symbol and func_symbol.name not in self.BUILTIN_FUNCTIONS:
                    self._calls[self._current_function].add(func_symbol.qualified_name)
                else:
                    static_target = self.module_graph.resolve_static_method_target(
                        self._current_module, path
                    )
                    if static_target:
                        struct_symbol, method_name = static_target
                        self._add_struct_usage(struct_symbol.qualified_name, method_name)

        if isinstance(ctx, ZincParser.SpawnStatementContext):
            path = extract_identifier_path(ctx.expression())
            if path:
                func_symbol = self.module_graph.resolve_function_path(self._current_module, path)
                if func_symbol and func_symbol.name not in self.BUILTIN_FUNCTIONS:
                    self._calls[self._current_function].add(func_symbol.qualified_name)

        if isinstance(ctx, ZincParser.StructInstantiationContext):
            struct_symbol = self.module_graph.resolve_struct_path(
                self._current_module, struct_path_from_ctx(ctx)
            )
            if struct_symbol:
                self._add_struct_usage(struct_symbol.qualified_name, None)

        for i in range(ctx.getChildCount()):
            child = ctx.getChild(i)
            if isinstance(child, ParserRuleContext):
                self._walk_for_references(child)

    def _add_struct_usage(self, qualified_name: str, method_name: str | None) -> None:
        """Record that a struct is used, optionally with a specific method."""
        struct = self._struct_defs.get(qualified_name)
        if struct is None:
            return

        if qualified_name not in self._reachable_structs:
            self._reachable_structs[qualified_name] = StructInstance(
                name=struct.name,
                qualified_name=struct.qualified_name,
                module_id=struct.module_id,
                ctx=struct.ctx,
                methods_used=SortedSet(),
            )

        if method_name:
            self._reachable_structs[qualified_name].methods_used.add(method_name)

        if self._current_function:
            self._struct_usages[self._current_function].add(qualified_name)

        self._add_composition_source_usages(qualified_name, set())

    def _add_composition_source_usages(self, qualified_name: str, seen: set[str]) -> None:
        """Mark structs referenced by a composition clause as reachable too."""
        if qualified_name in seen:
            return
        seen.add(qualified_name)

        struct = self._struct_defs.get(qualified_name)
        if struct is None:
            return

        composition = struct_composition_from_ctx(struct.ctx)
        if composition is None:
            return

        for path in composition.source_paths:
            source_symbol = self.module_graph.resolve_struct_path(struct.module_id, list(path))
            if source_symbol is None:
                continue
            source_struct = self._struct_defs.get(source_symbol.qualified_name)
            if source_struct is None:
                continue
            if source_symbol.qualified_name not in self._reachable_structs:
                self._reachable_structs[source_symbol.qualified_name] = StructInstance(
                    name=source_struct.name,
                    qualified_name=source_struct.qualified_name,
                    module_id=source_struct.module_id,
                    ctx=source_struct.ctx,
                    methods_used=SortedSet(),
                )
            self._add_composition_source_usages(source_symbol.qualified_name, seen)

    def _add_const_usage(self, qualified_name: str) -> None:
        """Record that a global constant is used."""
        const = self._const_defs.get(qualified_name)
        if const is None:
            return

        if qualified_name not in self._reachable_consts:
            self._reachable_consts[qualified_name] = ConstInstance(
                name=const.name,
                qualified_name=const.qualified_name,
                module_id=const.module_id,
                ctx=const.ctx,
            )

        if self._current_function:
            self._const_usages[self._current_function].add(qualified_name)
