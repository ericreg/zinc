"""Package and module loading for the Zinc compiler."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
import tomllib

from antlr4 import CommonTokenStream, InputStream, ParserRuleContext

from zinc.exceptions import ZincModuleError
from zinc.parser.zincLexer import zincLexer as ZincLexer
from zinc.parser.zincParser import zincParser as ZincParser


TopLevelKind = Literal["function", "struct", "const"]

PKG_FILE_NAME = "pkg.toml"


@dataclass(frozen=True)
class ImportSpec:
    """A single import declaration."""

    module_path: str
    alias: str | None = None
    names: tuple[str, ...] = ()


@dataclass(frozen=True)
class TopLevelSymbol:
    """A top-level declaration inside a module."""

    qualified_name: str
    module_id: str
    name: str
    kind: TopLevelKind
    ctx: ParserRuleContext
    is_public: bool


@dataclass
class LoadedModule:
    """A parsed Zinc module."""

    module_id: str
    path: Path
    tree: ZincParser.ProgramContext
    imports: list[ImportSpec]
    symbols: dict[str, TopLevelSymbol]
    exports: dict[str, TopLevelSymbol]
    injected_symbols: dict[str, str] = field(default_factory=dict)
    alias_imports: dict[str, str] = field(default_factory=dict)


@dataclass
class ModuleGraph:
    """All modules reachable from a single entry file."""

    package_root: Path
    entry_file: Path
    entry_module_id: str
    modules: dict[str, LoadedModule]
    top_level_symbols: dict[str, TopLevelSymbol]
    package_name: str
    package_version: str

    @staticmethod
    def qualified_name(module_id: str, name: str) -> str:
        """Build a canonical top-level symbol id."""
        return f"{module_id}::{name}"

    @staticmethod
    def split_qualified_name(qualified_name: str) -> tuple[str, str]:
        """Split a canonical symbol id into module id and local name."""
        module_id, _, name = qualified_name.partition("::")
        return module_id, name

    def module_token(self, module_id: str) -> str:
        """Return a Rust-safe token for a module id."""
        return module_id.replace("/", "_")

    def rust_base_name(self, qualified_name: str) -> str:
        """Return the flattened Rust base name for a top-level symbol."""
        module_id, name = self.split_qualified_name(qualified_name)
        return f"{self.module_token(module_id)}__{name}"

    def get_module(self, module_id: str) -> LoadedModule:
        """Look up a module by id."""
        return self.modules[module_id]

    def get_symbol(self, qualified_name: str) -> TopLevelSymbol:
        """Look up a top-level symbol by qualified id."""
        return self.top_level_symbols[qualified_name]

    def resolve_local_or_imported(self, module_id: str, name: str, kinds: set[TopLevelKind] | None = None) -> TopLevelSymbol | None:
        """Resolve a bare top-level symbol within a module."""
        module = self.modules[module_id]
        symbol = module.symbols.get(name)
        if symbol and (kinds is None or symbol.kind in kinds):
            return symbol

        qualified_name = module.injected_symbols.get(name)
        if qualified_name is None:
            return None

        symbol = self.top_level_symbols[qualified_name]
        if kinds is None or symbol.kind in kinds:
            return symbol
        return None

    def resolve_export(self, module_id: str, name: str, kinds: set[TopLevelKind] | None = None) -> TopLevelSymbol | None:
        """Resolve a public export from a specific module."""
        symbol = self.modules[module_id].exports.get(name)
        if symbol and (kinds is None or symbol.kind in kinds):
            return symbol
        return None

    def resolve_alias(self, module_id: str, alias: str) -> str | None:
        """Resolve a module alias in the current module."""
        return self.modules[module_id].alias_imports.get(alias)

    def resolve_top_level_path(self, module_id: str, path: list[str], kinds: set[TopLevelKind] | None = None) -> TopLevelSymbol | None:
        """Resolve a top-level symbol path like ['foo'] or ['pkg', 'Thing']."""
        if not path:
            return None

        if len(path) == 1:
            return self.resolve_local_or_imported(module_id, path[0], kinds)

        alias_target = self.resolve_alias(module_id, path[0])
        if alias_target and len(path) == 2:
            return self.resolve_export(alias_target, path[1], kinds)

        return None

    def resolve_struct_path(self, module_id: str, path: list[str]) -> TopLevelSymbol | None:
        """Resolve a struct path for struct instantiation."""
        return self.resolve_top_level_path(module_id, path, {"struct"})

    def resolve_const_path(self, module_id: str, path: list[str]) -> TopLevelSymbol | None:
        """Resolve a const path for value expressions."""
        return self.resolve_top_level_path(module_id, path, {"const"})

    def resolve_function_path(self, module_id: str, path: list[str]) -> TopLevelSymbol | None:
        """Resolve a top-level function path."""
        return self.resolve_top_level_path(module_id, path, {"function"})

    def resolve_static_method_target(self, module_id: str, path: list[str]) -> tuple[TopLevelSymbol, str] | None:
        """Resolve a struct static-method target like ['Counter', 'new'] or ['fb', 'Counter', 'new']."""
        if len(path) == 2:
            struct_symbol = self.resolve_local_or_imported(module_id, path[0], {"struct"})
            if struct_symbol:
                return struct_symbol, path[1]
            return None

        if len(path) == 3:
            alias_target = self.resolve_alias(module_id, path[0])
            if alias_target is None:
                return None
            struct_symbol = self.resolve_export(alias_target, path[1], {"struct"})
            if struct_symbol:
                return struct_symbol, path[2]
        return None

    def path_for_module(self, module_id: str) -> Path:
        """Return the source file path for a module id."""
        return self.package_root / f"{module_id}.zn"

    def top_level_functions(self) -> dict[str, ParserRuleContext]:
        """Return all top-level function definitions keyed by qualified id."""
        return {
            symbol.qualified_name: symbol.ctx
            for symbol in self.top_level_symbols.values()
            if symbol.kind == "function"
        }


def find_package_root(entry_file: Path) -> Path:
    """Find the nearest package root containing pkg.toml."""
    resolved_file = entry_file.resolve()
    for candidate in (resolved_file.parent, *resolved_file.parents):
        pkg_file = candidate / PKG_FILE_NAME
        if pkg_file.exists():
            _read_pkg_metadata(pkg_file)
            return candidate
    raise ZincModuleError(f"missing {PKG_FILE_NAME} for {entry_file}")


def build_module_graph(entry_file: Path) -> ModuleGraph:
    """Load the entry module and all transitive imports."""
    resolved_entry = entry_file.resolve()
    package_root = find_package_root(resolved_entry)
    pkg_name, pkg_version = _read_pkg_metadata(package_root / PKG_FILE_NAME)
    entry_module_id = _module_id_from_path(package_root, resolved_entry)

    modules: dict[str, LoadedModule] = {}
    top_level_symbols: dict[str, TopLevelSymbol] = {}
    loading_stack: list[str] = []

    def load_module_file(module_file: Path) -> LoadedModule:
        module_id = _module_id_from_path(package_root, module_file)

        if module_id in loading_stack:
            cycle = " -> ".join([*loading_stack, module_id])
            raise ZincModuleError(f"cyclic imports are not supported: {cycle}")

        existing = modules.get(module_id)
        if existing:
            if existing.path != module_file.resolve():
                raise ZincModuleError(f"duplicate module id '{module_id}'")
            return existing

        loading_stack.append(module_id)
        try:
            tree = _parse_program(module_file)
            imports = _collect_imports(tree)
            symbols = _collect_top_level_symbols(tree, module_id)
            exports = {
                name: symbol
                for name, symbol in symbols.items()
                if symbol.is_public
            }
            module = LoadedModule(
                module_id=module_id,
                path=module_file.resolve(),
                tree=tree,
                imports=imports,
                symbols=symbols,
                exports=exports,
            )
            modules[module_id] = module

            for symbol in symbols.values():
                if symbol.qualified_name in top_level_symbols:
                    raise ZincModuleError(f"duplicate symbol id '{symbol.qualified_name}'")
                top_level_symbols[symbol.qualified_name] = symbol

            for import_spec in imports:
                target_path = _module_file_from_import(package_root, import_spec.module_path)
                load_module_file(target_path)

            return module
        finally:
            loading_stack.pop()

    load_module_file(resolved_entry)

    graph = ModuleGraph(
        package_root=package_root,
        entry_file=resolved_entry,
        entry_module_id=entry_module_id,
        modules=modules,
        top_level_symbols=top_level_symbols,
        package_name=pkg_name,
        package_version=pkg_version,
    )

    for module in graph.modules.values():
        _resolve_module_import_scope(graph, module)

    entry_module = graph.get_module(entry_module_id)
    if "main" not in entry_module.symbols or entry_module.symbols["main"].kind != "function":
        raise ZincModuleError(f"entry module '{entry_module_id}' must define fn main()")

    return graph


def extract_identifier_path(expr_ctx) -> list[str] | None:
    """Extract an identifier/member-access path from a parse tree expression."""
    if isinstance(expr_ctx, ZincParser.PrimaryExprContext):
        return extract_identifier_path(expr_ctx.primaryExpression())

    if isinstance(expr_ctx, ZincParser.PrimaryExpressionContext):
        if expr_ctx.IDENTIFIER():
            return [expr_ctx.IDENTIFIER().getText()]
        return None

    if isinstance(expr_ctx, ZincParser.MemberAccessExprContext):
        prefix = extract_identifier_path(expr_ctx.expression())
        if prefix is None:
            return None
        return [*prefix, expr_ctx.IDENTIFIER().getText()]

    return None


def struct_path_from_ctx(ctx: ZincParser.StructInstantiationContext) -> list[str]:
    """Extract the declared struct path from a struct instantiation node."""
    qualified = ctx.qualifiedName()
    return [token.getText() for token in qualified.IDENTIFIER()]


def _read_pkg_metadata(pkg_file: Path) -> tuple[str, str]:
    """Read and validate package metadata."""
    try:
        with pkg_file.open("rb") as handle:
            data = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ZincModuleError(f"failed to read {pkg_file}: {exc}") from exc

    package = data.get("package")
    if not isinstance(package, dict):
        raise ZincModuleError(f"{pkg_file} must define a [package] table")

    name = package.get("name")
    version = package.get("version")
    if not isinstance(name, str) or not name:
        raise ZincModuleError(f"{pkg_file} must define package.name")
    if not isinstance(version, str) or not version:
        raise ZincModuleError(f"{pkg_file} must define package.version")
    return name, version


def _module_id_from_path(package_root: Path, module_file: Path) -> str:
    """Convert a source path to a package-relative module id."""
    resolved_root = package_root.resolve()
    resolved_file = module_file.resolve()
    try:
        relative = resolved_file.relative_to(resolved_root)
    except ValueError as exc:
        raise ZincModuleError(f"module path escapes package root: {module_file}") from exc

    if relative.suffix != ".zn":
        raise ZincModuleError(f"module file must end with .zn: {module_file}")
    return relative.with_suffix("").as_posix()


def _module_file_from_import(package_root: Path, module_path: str) -> Path:
    """Resolve an import path to a source file."""
    target = (package_root / f"{module_path}.zn").resolve()
    resolved_root = package_root.resolve()
    try:
        target.relative_to(resolved_root)
    except ValueError as exc:
        raise ZincModuleError(f"import path escapes package root: {module_path}") from exc
    if not target.exists():
        raise ZincModuleError(f"module not found: {module_path}")
    return target


def _parse_program(module_file: Path) -> ZincParser.ProgramContext:
    """Parse a Zinc source file into a program tree."""
    source_text = module_file.read_text()
    input_stream = InputStream(source_text)
    lexer = ZincLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = ZincParser(stream)
    tree = parser.program()
    if parser.getNumberOfSyntaxErrors() > 0:
        raise ZincModuleError(
            f"found {parser.getNumberOfSyntaxErrors()} syntax error(s) while parsing {module_file}"
        )
    return tree


def _collect_imports(tree: ZincParser.ProgramContext) -> list[ImportSpec]:
    """Collect top-level imports from a module."""
    imports: list[ImportSpec] = []
    for stmt in tree.statement():
        import_ctx = stmt.importStatement()
        if import_ctx is None:
            continue
        module_path = import_ctx.importPath().getText()
        alias = None
        names: tuple[str, ...] = ()
        if import_ctx.importNameList():
            names = tuple(token.getText() for token in import_ctx.importNameList().IDENTIFIER())
        elif import_ctx.IDENTIFIER():
            alias = import_ctx.IDENTIFIER().getText()
        imports.append(ImportSpec(module_path=module_path, alias=alias, names=names))
    return imports


def _collect_top_level_symbols(tree: ZincParser.ProgramContext, module_id: str) -> dict[str, TopLevelSymbol]:
    """Collect top-level declarations from a module."""
    symbols: dict[str, TopLevelSymbol] = {}
    for stmt in tree.statement():
        symbol: TopLevelSymbol | None = None
        if stmt.functionDeclaration():
            ctx = stmt.functionDeclaration()
            name = ctx.IDENTIFIER().getText()
            symbol = TopLevelSymbol(
                qualified_name=ModuleGraph.qualified_name(module_id, name),
                module_id=module_id,
                name=name,
                kind="function",
                ctx=ctx,
                is_public=not name.startswith("_"),
            )
        elif stmt.structDeclaration():
            ctx = stmt.structDeclaration()
            name = ctx.IDENTIFIER().getText()
            symbol = TopLevelSymbol(
                qualified_name=ModuleGraph.qualified_name(module_id, name),
                module_id=module_id,
                name=name,
                kind="struct",
                ctx=ctx,
                is_public=not name.startswith("_"),
            )
        elif stmt.constDeclaration():
            ctx = stmt.constDeclaration()
            name = ctx.IDENTIFIER().getText()
            symbol = TopLevelSymbol(
                qualified_name=ModuleGraph.qualified_name(module_id, name),
                module_id=module_id,
                name=name,
                kind="const",
                ctx=ctx,
                is_public=not name.startswith("_"),
            )

        if symbol is None:
            continue
        if symbol.name in symbols:
            raise ZincModuleError(
                f"duplicate top-level declaration '{symbol.name}' in module '{module_id}'"
            )
        symbols[symbol.name] = symbol

    return symbols


def _resolve_module_import_scope(graph: ModuleGraph, module: LoadedModule) -> None:
    """Resolve and validate a module's import scope."""
    injected: dict[str, str] = {}
    aliases: dict[str, str] = {}
    local_names = set(module.symbols.keys())

    for import_spec in module.imports:
        target = graph.get_module(import_spec.module_path)

        if import_spec.alias:
            alias = import_spec.alias
            if alias in aliases:
                raise ZincModuleError(
                    f"duplicate import alias '{alias}' in module '{module.module_id}'"
                )
            if alias in injected or alias in local_names:
                raise ZincModuleError(
                    f"alias '{alias}' conflicts with an existing name in module '{module.module_id}'"
                )
            aliases[alias] = target.module_id
            continue

        import_names = import_spec.names or tuple(target.exports.keys())
        for name in import_names:
            export = target.exports.get(name)
            if export is None:
                raise ZincModuleError(
                    f"module '{target.module_id}' does not export '{name}'"
                )
            if name in local_names:
                raise ZincModuleError(
                    f"imported name '{name}' conflicts with a local declaration in module '{module.module_id}'"
                )
            if name in injected and injected[name] != export.qualified_name:
                raise ZincModuleError(
                    f"duplicate imported name '{name}' in module '{module.module_id}'"
                )
            injected[name] = export.qualified_name

    module.injected_symbols = injected
    module.alias_imports = aliases
