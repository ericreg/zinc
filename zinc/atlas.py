"""Atlas - Graph of all code reachable from main()."""

from dataclasses import dataclass, field
from antlr4 import ParserRuleContext

from zinc.ast.types import BaseType
from zinc.parser.zincVisitor import zincVisitor
from zinc.parser.zincParser import zincParser as ZincParser


@dataclass
class FunctionInstance:
    """A specific instantiation of a function (possibly monomorphized)."""

    name: str  # Original function name
    mangled_name: str  # Unique name (e.g., "add_i64_i64")
    ctx: ParserRuleContext  # Parse tree reference
    arg_types: list[BaseType]  # Concrete argument types


@dataclass
class StructInstance:
    """A struct that is used in the program."""

    name: str
    ctx: ParserRuleContext
    methods_used: set[str] = field(default_factory=set)  # Which methods are actually called


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
    functions: dict[str, FunctionInstance] = field(default_factory=dict)

    # All reachable structs (keyed by struct name)
    structs: dict[str, StructInstance] = field(default_factory=dict)

    # All reachable global constants (keyed by const name)
    consts: dict[str, ConstInstance] = field(default_factory=dict)

    # Call graph: caller mangled_name -> set of callee mangled_names
    calls: dict[str, set[str]] = field(default_factory=dict)

    # Struct usage: func mangled_name -> set of struct names used
    struct_usages: dict[str, set[str]] = field(default_factory=dict)

    # Const usage: func mangled_name -> set of const names used
    const_usages: dict[str, set[str]] = field(default_factory=dict)

    def is_reachable(self, name: str) -> bool:
        """Check if a function, struct, or const is reachable."""
        return name in self.functions or name in self.structs or name in self.consts

    def topological_order(self) -> list[str]:
        """Return function mangled_names in dependency order (callees first).

        Uses DFS-based topological sort.
        """
        visited: set[str] = set()
        result: list[str] = []

        def dfs(name: str) -> None:
            if name in visited:
                return
            visited.add(name)
            # Visit callees first
            for callee in self.calls.get(name, set()):
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
        self._function_defs: dict[str, ParserRuleContext] = {}  # name -> ctx
        self._struct_defs: dict[str, ParserRuleContext] = {}  # name -> ctx
        self._const_defs: dict[str, ParserRuleContext] = {}  # name -> ctx
        self._main_ctx: ParserRuleContext | None = None

        # Reachability tracking
        self._reachable_functions: dict[str, FunctionInstance] = {}
        self._reachable_structs: dict[str, StructInstance] = {}
        self._reachable_consts: dict[str, ConstInstance] = {}

        # Graph edges (populated during reachability walk)
        self._calls: dict[str, set[str]] = {}
        self._struct_usages: dict[str, set[str]] = {}
        self._const_usages: dict[str, set[str]] = {}

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
        """
        if self._main_ctx is None:
            raise ValueError("No main() function found")

        # Create main function instance
        main_instance = FunctionInstance(
            name="main",
            mangled_name="main",
            ctx=self._main_ctx,
            arg_types=[],
        )
        self._reachable_functions["main"] = main_instance

        # Worklist algorithm: discover reachable code
        worklist = ["main"]
        visited: set[str] = set()

        while worklist:
            func_name = worklist.pop()
            if func_name in visited:
                continue
            visited.add(func_name)

            if func_name not in self._reachable_functions:
                continue

            func = self._reachable_functions[func_name]
            self._current_function = func.mangled_name
            self._calls[func.mangled_name] = set()
            self._struct_usages[func.mangled_name] = set()
            self._const_usages[func.mangled_name] = set()

            # Walk the function body to find calls, struct usages, and const usages
            self._walk_for_references(func.ctx)

            # Add discovered functions to worklist
            for callee in self._calls[func.mangled_name]:
                if callee not in visited and callee in self._function_defs:
                    # Create function instance if not exists
                    if callee not in self._reachable_functions:
                        callee_ctx = self._function_defs[callee]
                        self._reachable_functions[callee] = FunctionInstance(
                            name=callee,
                            mangled_name=callee,  # Will be updated during type resolution
                            ctx=callee_ctx,
                            arg_types=[],  # Will be populated during type resolution
                        )
                    worklist.append(callee)

        return Atlas(
            main=main_instance,
            functions=self._reachable_functions,
            structs=self._reachable_structs,
            consts=self._reachable_consts,
            calls=self._calls,
            struct_usages=self._struct_usages,
            const_usages=self._const_usages,
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
                methods_used=set(),
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
