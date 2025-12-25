"""Atlas - Graph of all code reachable from main()."""

from dataclasses import dataclass, field
from antlr4 import ParserRuleContext
from sortedcontainers import SortedDict, SortedSet

from zinc.ast.types import BaseType, type_to_rust, ChannelTypeInfo
from zinc.parser.zincVisitor import zincVisitor
from zinc.parser.zincParser import zincParser as ZincParser


@dataclass
class FunctionInstance:
    """A specific instantiation of a function (possibly monomorphized)."""

    name: str  # Original function name
    mangled_name: str  # Unique name (e.g., "add_i64_i64")
    ctx: ParserRuleContext  # Parse tree reference
    arg_types: list[BaseType]  # Concrete argument types
    return_type: BaseType = field(default=BaseType.VOID)  # Inferred return type
    is_async: bool = False  # True if called via spawn (becomes async fn)
    # Rich type info for channel arguments (arg_index -> ChannelTypeInfo)
    arg_channel_infos: dict[int, ChannelTypeInfo] = field(default_factory=dict)


@dataclass
class StructFieldInfo:
    """Analyzed struct field information."""

    name: str
    type_annotation: str | None = None  # Explicit type like "i32", "string"
    default_value: str | None = None  # Default value expression text
    is_private: bool = False  # Starts with _
    is_const: bool = False  # Has 'const' modifier
    resolved_type: BaseType = field(default=BaseType.UNKNOWN)

    def rust_type(self) -> str:
        """Get Rust type string for this field."""
        if self.type_annotation:
            # Map zinc types to Rust
            mapping = {
                "i32": "i32",
                "i64": "i64",
                "f32": "f32",
                "f64": "f64",
                "string": "String",
                "bool": "bool",
            }
            return mapping.get(self.type_annotation.lower(), self.type_annotation)
        return type_to_rust(self.resolved_type)

    def rust_default(self) -> str:
        """Get Rust default value for this field."""
        if self.default_value:
            # Handle string literals
            if self.rust_type() == "String" and self.default_value.startswith('"'):
                return f"String::from({self.default_value})"
            return self.default_value
        # Zero-initialize based on type
        defaults = {
            "i32": "0",
            "i64": "0",
            "f32": "0.0",
            "f64": "0.0",
            "String": "String::new()",
            "bool": "false",
        }
        return defaults.get(self.rust_type(), "Default::default()")


@dataclass
class StructMethodInfo:
    """Analyzed struct method information."""

    name: str
    parameters: list[tuple[str, str | None, str | None]] = field(
        default_factory=list
    )  # (name, type_annotation, resolved_type)
    is_static: bool = False  # True if no self usage
    self_mutability: str | None = None  # None, "&self", or "&mut self"
    return_type: str | None = None
    body_ctx: ParserRuleContext | None = None  # For codegen


@dataclass
class StructInstance:
    """A struct that is used in the program."""

    name: str
    ctx: ParserRuleContext
    methods_used: SortedSet[str] = field(default_factory=SortedSet)  # Which methods are actually called
    # Analyzed data (populated by SymbolTableVisitor)
    fields: list[StructFieldInfo] = field(default_factory=list)
    methods: list[StructMethodInfo] = field(default_factory=list)


@dataclass
class ConstInstance:
    """A global constant declaration."""

    name: str
    ctx: ParserRuleContext


@dataclass
class Atlas:
    """Graph of all code reachable from main()."""

    # Entry point
    main: FunctionInstance

    # All reachable functions (keyed by mangled_name)
    functions: SortedDict[str, FunctionInstance] = field(default_factory=SortedDict)

    # All reachable structs (keyed by struct name)
    structs: SortedDict[str, StructInstance] = field(default_factory=SortedDict)

    # All reachable global constants (keyed by const name)
    consts: SortedDict[str, ConstInstance] = field(default_factory=SortedDict)

    # Call graph: caller mangled_name -> set of callee mangled_names
    calls: SortedDict[str, SortedSet[str]] = field(default_factory=SortedDict)

    # Struct usage: func mangled_name -> set of struct names used
    struct_usages: SortedDict[str, SortedSet[str]] = field(default_factory=SortedDict)

    # Const usage: func mangled_name -> set of const names used
    const_usages: SortedDict[str, SortedSet[str]] = field(default_factory=SortedDict)

    # Raw function definitions (name -> ctx) for specialization creation
    function_defs: SortedDict[str, ParserRuleContext] = field(default_factory=SortedDict)

    def is_reachable(self, name: str) -> bool:
        """Check if a function, struct, or const is reachable."""
        return name in self.functions or name in self.structs or name in self.consts

    def add_specialization(
        self,
        name: str,
        arg_types: list[BaseType],
        ctx: ParserRuleContext,
        caller_mangled: str | None = None,
    ) -> str:
        """Create a new function specialization. Returns mangled name.

        If caller_mangled is provided, updates the call graph to record that
        caller_mangled calls this specialization.
        """
        mangled = self._mangle_name(name, arg_types)
        if mangled not in self.functions:
            self.functions[mangled] = FunctionInstance(
                name=name,
                mangled_name=mangled,
                ctx=ctx,
                arg_types=list(arg_types),  # Copy to avoid mutation
            )
            # Initialize call graph entry for the new specialization
            self.calls[mangled] = SortedSet()

        # Update call graph: caller calls this specialization
        if caller_mangled and caller_mangled in self.calls:
            self.calls[caller_mangled].add(mangled)

        return mangled

    def _mangle_name(self, name: str, arg_types: list[BaseType]) -> str:
        """Generate mangled name like 'add_i64_i64'."""
        if not arg_types:
            return name
        type_suffix = "_".join(type_to_rust(t) for t in arg_types)
        return f"{name}_{type_suffix}"

    def topological_order(self) -> list[str]:
        """Return function mangled_names in dependency order (callees first).

        Uses DFS-based topological sort. Only considers functions that exist
        in self.functions (i.e., have been specialized).
        """
        visited: set[str] = set()
        result: list[str] = []

        def dfs(name: str) -> None:
            if name in visited:
                return
            # Only process functions that actually exist
            if name not in self.functions:
                return
            visited.add(name)
            # Visit callees first (only those that exist as specializations)
            for callee in self.calls.get(name, set()):
                if callee in self.functions:
                    dfs(callee)
            result.append(name)

        # Start DFS from all functions
        for name in self.functions:
            dfs(name)

        return result


class AtlasBuilder(zincVisitor):
    """Builds an Atlas by walking from main() and discovering reachable code."""

    def __init__(self):
        # Collected definitions (first pass)
        self._function_defs: SortedDict[str, ParserRuleContext] = SortedDict()  # name -> ctx
        self._struct_defs: SortedDict[str, ParserRuleContext] = SortedDict()  # name -> ctx
        self._const_defs: SortedDict[str, ParserRuleContext] = SortedDict()  # name -> ctx
        self._main_ctx: ParserRuleContext | None = None

        # Reachability tracking
        self._reachable_functions: SortedDict[str, FunctionInstance] = SortedDict()
        self._reachable_structs: SortedDict[str, StructInstance] = SortedDict()
        self._reachable_consts: SortedDict[str, ConstInstance] = SortedDict()

        # Graph edges (populated during reachability walk)
        self._calls: SortedDict[str, SortedSet[str]] = SortedDict()
        self._struct_usages: SortedDict[str, SortedSet[str]] = SortedDict()
        self._const_usages: SortedDict[str, SortedSet[str]] = SortedDict()

        # Current context for edge building
        self._current_function: str | None = None

    def visitFunctionDeclaration(self, ctx: ZincParser.FunctionDeclarationContext):
        """Collect function definition."""
        name = ctx.IDENTIFIER().getText()
        self._function_defs[name] = ctx
        if name == "main":
            self._main_ctx = ctx
        return self.visitChildren(ctx)

    def visitStructDeclaration(self, ctx: ZincParser.StructDeclarationContext):
        """Collect struct definition."""
        name = ctx.IDENTIFIER().getText()
        self._struct_defs[name] = ctx
        return self.visitChildren(ctx)

    def visitConstDeclaration(self, ctx: ZincParser.ConstDeclarationContext):
        """Collect const definition."""
        name = ctx.IDENTIFIER().getText()
        self._const_defs[name] = ctx
        return self.visitChildren(ctx)

    def build(self) -> Atlas:
        """Build the Atlas after visiting the parse tree.

        Uses worklist algorithm to discover reachable code from main.
        Only creates FunctionInstance for main - other functions get their
        FunctionInstances created by SymbolTableVisitor during monomorphization.
        """
        if self._main_ctx is None:
            raise ValueError("No main() function found")

        # Create main function instance (only main is created here)
        main_instance = FunctionInstance(
            name="main",
            mangled_name="main",
            ctx=self._main_ctx,
            arg_types=[],
        )
        self._reachable_functions["main"] = main_instance

        # Worklist algorithm: discover reachable functions (but don't create instances)
        worklist = ["main"]
        visited: set[str] = set()
        reachable_func_names: set[str] = {"main"}

        while worklist:
            func_name = worklist.pop()
            if func_name in visited:
                continue
            visited.add(func_name)

            # Get function ctx - either from reachable_functions or function_defs
            if func_name in self._reachable_functions:
                func_ctx = self._reachable_functions[func_name].ctx
            elif func_name in self._function_defs:
                func_ctx = self._function_defs[func_name]
            else:
                continue

            self._current_function = func_name
            self._calls[func_name] = SortedSet()
            self._struct_usages[func_name] = SortedSet()
            self._const_usages[func_name] = SortedSet()

            # Walk the function body to find calls, struct usages, and const usages
            self._walk_for_references(func_ctx)

            # Add discovered functions to worklist (but don't create FunctionInstances)
            for callee in self._calls[func_name]:
                if callee not in visited and callee in self._function_defs:
                    reachable_func_names.add(callee)
                    worklist.append(callee)

        return Atlas(
            main=main_instance,
            functions=self._reachable_functions,  # Only contains main at this point
            structs=self._reachable_structs,
            consts=self._reachable_consts,
            calls=self._calls,
            struct_usages=self._struct_usages,
            const_usages=self._const_usages,
            function_defs=self._function_defs,
        )

    def _walk_for_references(self, ctx: ParserRuleContext) -> None:
        """Walk a parse tree node to find function calls, struct usages, and const usages."""
        if ctx is None:
            return

        # Check for identifier reference (could be a const)
        if isinstance(ctx, ZincParser.PrimaryExpressionContext):
            if ctx.IDENTIFIER():
                name = ctx.IDENTIFIER().getText()
                if name in self._const_defs:
                    self._add_const_usage(name)

        # Check for function call
        if isinstance(ctx, ZincParser.FunctionCallExprContext):
            # Get the callee - could be an identifier or member access
            callee_ctx = ctx.expression()
            callee_text = callee_ctx.getText()

            # Simple function call (not a method call)
            if isinstance(callee_ctx, ZincParser.PrimaryExprContext):
                primary = callee_ctx.primaryExpression()
                if primary and primary.IDENTIFIER():
                    func_name = primary.IDENTIFIER().getText()
                    # Skip builtins like print, chan
                    if func_name not in ("print", "chan"):
                        self._calls[self._current_function].add(func_name)

            # Method call on struct type (static method)
            elif isinstance(callee_ctx, ZincParser.MemberAccessExprContext):
                target = callee_ctx.expression().getText()
                if target in self._struct_defs:
                    self._add_struct_usage(target, callee_ctx.IDENTIFIER().getText())

        # Check for spawn statement - spawn expr(args) where expr is function name
        if isinstance(ctx, ZincParser.SpawnStatementContext):
            expr = ctx.expression()
            # The expression is the function name (e.g., greet in "spawn greet(42)")
            if isinstance(expr, ZincParser.PrimaryExprContext):
                primary = expr.primaryExpression()
                if primary and primary.IDENTIFIER():
                    func_name = primary.IDENTIFIER().getText()
                    if func_name not in ("print", "chan") and self._current_function:
                        self._calls[self._current_function].add(func_name)

        # Check for struct instantiation
        if isinstance(ctx, ZincParser.StructInstantiationContext):
            struct_name = ctx.IDENTIFIER().getText()
            self._add_struct_usage(struct_name, None)

        # Check for method call on identifier (instance method)
        if isinstance(ctx, ZincParser.MemberAccessExprContext):
            # Check if the target is a known struct type
            target_text = ctx.expression().getText()
            if target_text in self._struct_defs:
                method_name = ctx.IDENTIFIER().getText()
                self._add_struct_usage(target_text, method_name)

        # Recurse into children
        for i in range(ctx.getChildCount()):
            child = ctx.getChild(i)
            if isinstance(child, ParserRuleContext):
                self._walk_for_references(child)

    def _add_struct_usage(self, struct_name: str, method_name: str | None) -> None:
        """Record that a struct is used, optionally with a specific method."""
        if struct_name not in self._struct_defs:
            return

        if struct_name not in self._reachable_structs:
            self._reachable_structs[struct_name] = StructInstance(
                name=struct_name,
                ctx=self._struct_defs[struct_name],
                methods_used=SortedSet(),
            )

        if method_name:
            self._reachable_structs[struct_name].methods_used.add(method_name)

        if self._current_function:
            self._struct_usages[self._current_function].add(struct_name)

    def _add_const_usage(self, const_name: str) -> None:
        """Record that a global constant is used."""
        if const_name not in self._const_defs:
            return

        if const_name not in self._reachable_consts:
            self._reachable_consts[const_name] = ConstInstance(
                name=const_name,
                ctx=self._const_defs[const_name],
            )

        if self._current_function:
            self._const_usages[self._current_function].add(const_name)
