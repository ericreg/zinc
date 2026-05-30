"""Package and module loading for the Zinc compiler."""

from __future__ import annotations

import tomllib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from antlr4 import CommonTokenStream, InputStream, ParserRuleContext
from zinc.exceptions import ZincModuleError
from zinc.parser.zincLexer import zincLexer as ZincLexer
from zinc.parser.zincParser import zincParser as ZincParser

RESERVED_ERROR_NAMES = frozenset({"Ok", "Err", "Some", "None"})

TopLevelKind = Literal["function", "struct", "enum", "const"]
CompositionMode = Literal["orthogonal", "merge"]

PKG_FILE_NAME = "pkg.toml"


@dataclass(frozen=True)
class ImportSpec:
    """A single import declaration."""

    module_path: str
    alias: str | None = None
    names: tuple[str, ...] = ()


@dataclass(frozen=True)
class RustExternParameter:
    """A parameter declared in an extern Rust function signature."""

    name: str
    type_text: str | None = None
    is_self: bool = False


@dataclass(frozen=True)
class RustExternFunction:
    """A Rust function or method declaration visible to Zinc."""

    name: str
    params: tuple[RustExternParameter, ...]
    return_type: str | None = None
    is_async: bool = False
    owner_type: str | None = None
    is_static: bool = True
    display_name: str | None = None


@dataclass(frozen=True)
class RustExternType:
    """An opaque Rust-owned type visible to Zinc."""

    name: str
    qualified_name: str
    module_id: str
    rust_name: str


@dataclass(frozen=True)
class RustExternBlock:
    """Rust interop declarations extracted from one extern rust block."""

    uses: tuple[str, ...] = ()
    types: tuple[str, ...] = ()
    functions: tuple[RustExternFunction, ...] = ()


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
    rust_uses: list[str]
    rust_extern_types: dict[str, RustExternType]
    rust_extern_functions: dict[str, RustExternFunction]
    rust_extern_methods: dict[tuple[str, str], RustExternFunction]
    symbols: dict[str, TopLevelSymbol]
    exports: dict[str, TopLevelSymbol]
    injected_symbols: dict[str, str] = field(default_factory=dict)
    alias_imports: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class StructCompositionSpec:
    """Composition clause attached to a struct declaration."""

    mode: CompositionMode
    source_paths: tuple[tuple[str, ...], ...]


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
    def extern_type_qualified_name(module_id: str, name: str) -> str:
        """Build a canonical opaque Rust type id."""
        return f"{module_id}::extern::{name}"

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

    def is_extern_type_qualified_name(self, qualified_name: str | None) -> bool:
        """Return True if a qualified name refers to an opaque Rust type."""
        if qualified_name is None:
            return False
        return self.extern_type_by_qualified_name(qualified_name) is not None

    def extern_type_by_qualified_name(self, qualified_name: str) -> RustExternType | None:
        """Look up an opaque Rust type by canonical id."""
        for module in self.modules.values():
            for extern_type in module.rust_extern_types.values():
                if extern_type.qualified_name == qualified_name:
                    return extern_type
        return None

    def extern_type_rust_name(self, qualified_name: str | None) -> str | None:
        """Return the Rust spelling for an opaque Rust type."""
        if qualified_name is None:
            return None
        extern_type = self.extern_type_by_qualified_name(qualified_name)
        return extern_type.rust_name if extern_type is not None else None

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

    def resolve_enum_path(self, module_id: str, path: list[str]) -> TopLevelSymbol | None:
        """Resolve an enum path for annotations and value construction."""
        return self.resolve_top_level_path(module_id, path, {"enum"})

    def resolve_const_path(self, module_id: str, path: list[str]) -> TopLevelSymbol | None:
        """Resolve a const path for value expressions."""
        return self.resolve_top_level_path(module_id, path, {"const"})

    def resolve_function_path(self, module_id: str, path: list[str]) -> TopLevelSymbol | None:
        """Resolve a top-level function path."""
        return self.resolve_top_level_path(module_id, path, {"function"})

    def resolve_extern_type_path(self, module_id: str, path: list[str]) -> RustExternType | None:
        """Resolve an opaque Rust type visible from a module."""
        if len(path) != 1:
            return None
        return self.modules[module_id].rust_extern_types.get(path[0])

    def resolve_extern_function_path(self, module_id: str, path: list[str]) -> RustExternFunction | None:
        """Resolve a free Rust function visible from a module."""
        if len(path) != 1:
            return None
        return self.modules[module_id].rust_extern_functions.get(path[0])

    def rust_use_imports_name(self, module_id: str, name: str) -> bool:
        """Return True when a raw extern Rust use appears to introduce a name."""
        return any(_rust_use_imports_name(rust_use, name) for rust_use in self.modules[module_id].rust_uses)

    def resolve_extern_static_method_path(self, module_id: str, path: list[str]) -> RustExternFunction | None:
        """Resolve an opaque Rust associated function like ['FileHandle', 'open']."""
        if len(path) != 2:
            return None
        owner = self.resolve_extern_type_path(module_id, [path[0]])
        if owner is None:
            return None
        func = self.modules[module_id].rust_extern_methods.get((owner.qualified_name, path[1]))
        if func is not None and func.is_static:
            return func
        return None

    def resolve_extern_instance_method(self, module_id: str, owner_qualified_name: str, method_name: str) -> RustExternFunction | None:
        """Resolve an opaque Rust instance method for a known receiver type."""
        func = self.modules[module_id].rust_extern_methods.get((owner_qualified_name, method_name))
        if func is not None and not func.is_static:
            return func
        return None

    def resolve_static_method_target(self, module_id: str, path: list[str]) -> tuple[TopLevelSymbol, str] | None:
        """Resolve a struct/enum static-method target like ['Counter', 'new'] or ['fb', 'Counter', 'new']."""
        if len(path) == 2:
            type_symbol = self.resolve_local_or_imported(module_id, path[0], {"struct", "enum"})
            if type_symbol:
                return type_symbol, path[1]
            return None

        if len(path) == 3:
            alias_target = self.resolve_alias(module_id, path[0])
            if alias_target is None:
                return None
            type_symbol = self.resolve_export(alias_target, path[1], {"struct", "enum"})
            if type_symbol:
                return type_symbol, path[2]
        return None

    def resolve_enum_variant_path(self, module_id: str, path: list[str]) -> tuple[TopLevelSymbol, str] | None:
        """Resolve an enum variant path like ['Message', 'Quit'] or ['pkg', 'Message', 'Quit']."""
        if len(path) < 2:
            return None
        enum_symbol = self.resolve_enum_path(module_id, path[:-1])
        if enum_symbol is None:
            return None
        return enum_symbol, path[-1]

    def path_for_module(self, module_id: str) -> Path:
        """Return the source file path for a module id."""
        return self.package_root / f"{module_id}.zn"

    def top_level_functions(self) -> dict[str, ParserRuleContext]:
        """Return all top-level function definitions keyed by qualified id."""
        return {symbol.qualified_name: symbol.ctx for symbol in self.top_level_symbols.values() if symbol.kind == "function"}


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
            tree, extern_block = _parse_program(module_file)
            imports = _collect_imports(tree)
            symbols = _collect_top_level_symbols(tree, module_id)
            exports = {name: symbol for name, symbol in symbols.items() if symbol.is_public}
            duplicate_extern_types = {name for name in extern_block.types if extern_block.types.count(name) > 1}
            if duplicate_extern_types:
                duplicate = sorted(duplicate_extern_types)[0]
                raise ZincModuleError(f"duplicate extern rust type '{duplicate}' in module '{module_id}'")
            rust_extern_types = {
                name: RustExternType(
                    name=name,
                    qualified_name=ModuleGraph.extern_type_qualified_name(module_id, name),
                    module_id=module_id,
                    rust_name=name,
                )
                for name in extern_block.types
            }
            rust_extern_functions: dict[str, RustExternFunction] = {}
            rust_extern_methods: dict[tuple[str, str], RustExternFunction] = {}
            for function in extern_block.functions:
                if function.owner_type is None:
                    if function.name in rust_extern_functions:
                        raise ZincModuleError(f"duplicate extern rust function '{function.name}' in module '{module_id}'")
                    rust_extern_functions[function.name] = function
                    continue
                owner = rust_extern_types.get(function.owner_type)
                if owner is None:
                    raise ZincModuleError(f"extern rust impl references unknown type '{function.owner_type}'")
                key = (owner.qualified_name, function.name)
                if key in rust_extern_methods:
                    raise ZincModuleError(
                        f"duplicate extern rust method '{function.owner_type}.{function.name}' in module '{module_id}'"
                    )
                rust_extern_methods[key] = function
            module = LoadedModule(
                module_id=module_id,
                path=module_file.resolve(),
                tree=tree,
                imports=imports,
                rust_uses=list(extern_block.uses),
                rust_extern_types=rust_extern_types,
                rust_extern_functions=rust_extern_functions,
                rust_extern_methods=rust_extern_methods,
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
        if hasattr(expr_ctx, "TYPE_KW") and expr_ctx.TYPE_KW():
            return [expr_ctx.TYPE_KW().getText()]
        return None

    if isinstance(expr_ctx, ZincParser.MemberAccessExprContext):
        prefix = extract_identifier_path(expr_ctx.expression())
        if prefix is None:
            return None
        return [*prefix, expr_ctx.IDENTIFIER().getText()]

    return None


def struct_path_from_ctx(ctx: ZincParser.StructInstantiationContext) -> list[str]:
    """Extract the declared struct path from a struct instantiation node."""
    return qualified_name_path(ctx.qualifiedName())


def enum_variant_path_from_ctx(ctx: ZincParser.EnumVariantConstructionContext) -> list[str]:
    """Extract the enum variant path from an enum variant construction node."""
    parts = qualified_name_path(ctx.enumVariantPath().qualifiedName())
    parts.append(ctx.enumVariantPath().IDENTIFIER().getText())
    return parts


def qualified_name_path(ctx: ZincParser.QualifiedNameContext) -> list[str]:
    """Extract identifier parts from a qualified name."""
    return [token.getText() for token in ctx.IDENTIFIER()]


def struct_composition_from_ctx(
    ctx: ZincParser.StructDeclarationContext,
) -> StructCompositionSpec | None:
    """Return composition metadata for a struct declaration, if present."""
    composition = ctx.structComposition()
    if composition is None:
        return None

    if composition.orthogonalComposition():
        sources = tuple(tuple(qualified_name_path(qualified)) for qualified in composition.orthogonalComposition().qualifiedName())
        return StructCompositionSpec(
            mode="merge" if len(sources) == 1 else "orthogonal",
            source_paths=sources,
        )

    if composition.mergeComposition():
        return StructCompositionSpec(
            mode="merge",
            source_paths=tuple(tuple(qualified_name_path(qualified)) for qualified in composition.mergeComposition().qualifiedName()),
        )

    return None


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


def _parse_program(module_file: Path) -> tuple[ZincParser.ProgramContext, RustExternBlock]:
    """Parse a Zinc source file into a program tree and extracted Rust extern metadata."""
    source_text = module_file.read_text()
    stripped_text, extern_block = _extract_rust_extern_blocks(source_text)
    input_stream = InputStream(stripped_text)
    lexer = ZincLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = ZincParser(stream)
    tree = parser.program()
    if parser.getNumberOfSyntaxErrors() > 0:
        raise ZincModuleError(f"found {parser.getNumberOfSyntaxErrors()} syntax error(s) while parsing {module_file}")
    return tree, extern_block


def _extract_rust_extern_blocks(source_text: str) -> tuple[str, RustExternBlock]:
    """Extract extern rust blocks and replace them with whitespace for normal Zinc parsing."""
    uses: list[str] = []
    types: list[str] = []
    functions: list[RustExternFunction] = []
    replacements = list(source_text)
    cursor = 0

    while True:
        match = re.search(r"\bextern\s+rust\s*\{", source_text[cursor:])
        if match is None:
            break
        start = cursor + match.start()
        open_brace = cursor + match.end() - 1
        close_brace = _find_matching_brace(source_text, open_brace)
        if close_brace is None:
            raise ZincModuleError("unterminated extern rust block")
        body = source_text[open_brace + 1 : close_brace]
        block = _parse_rust_extern_body(body)
        uses.extend(block.uses)
        types.extend(block.types)
        functions.extend(block.functions)
        for index in range(start, close_brace + 1):
            replacements[index] = "\n" if source_text[index] == "\n" else " "
        cursor = close_brace + 1

    return "".join(replacements), RustExternBlock(uses=tuple(uses), types=tuple(types), functions=tuple(functions))


def _find_matching_brace(text: str, open_index: int) -> int | None:
    """Find a matching brace while ignoring strings and comments."""
    depth = 0
    i = open_index
    quote: str | None = None
    while i < len(text):
        char = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if quote is not None:
            if char == "\\":
                i += 2
                continue
            if quote == "`" and char == "`" and nxt == "`":
                i += 2
                continue
            if char == quote:
                quote = None
            i += 1
            continue
        if char in {'"', "'", "`"}:
            quote = char
            i += 1
            continue
        if char == "/" and nxt == "/":
            newline = text.find("\n", i + 2)
            if newline == -1:
                return None
            i = newline + 1
            continue
        if char == "/" and nxt == "*":
            end = text.find("*/", i + 2)
            if end == -1:
                return None
            i = end + 2
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return None


def _parse_rust_extern_body(body: str) -> RustExternBlock:
    """Parse the supported declarations inside an extern rust block."""
    uses: list[str] = []
    types: list[str] = []
    functions: list[RustExternFunction] = []
    cursor = 0

    while cursor < len(body):
        cursor = _skip_extern_ws(body, cursor)
        if cursor >= len(body):
            break
        if _body_startswith_kw(body, cursor, "use"):
            statement, cursor = _read_semicolon_item(body, cursor)
            uses.append(statement.strip())
            continue
        if _body_startswith_kw(body, cursor, "type"):
            statement, cursor = _read_semicolon_item(body, cursor)
            match = re.fullmatch(r"type\s+([A-Za-z_][A-Za-z0-9_]*)\s*;", statement.strip())
            if match is None:
                raise ZincModuleError(f"invalid extern rust type declaration: {statement.strip()}")
            types.append(match.group(1))
            continue
        if _body_startswith_kw(body, cursor, "fn") or _body_startswith_kw(body, cursor, "async"):
            statement, cursor = _read_semicolon_item(body, cursor)
            functions.append(_parse_rust_extern_function(statement))
            continue
        if _body_startswith_kw(body, cursor, "impl"):
            impl_functions, cursor = _parse_rust_extern_impl(body, cursor)
            functions.extend(impl_functions)
            continue
        raise ZincModuleError(f"unsupported extern rust item near: {body[cursor:cursor + 40].strip()}")

    return RustExternBlock(uses=tuple(uses), types=tuple(types), functions=tuple(functions))


def _skip_extern_ws(text: str, cursor: int) -> int:
    """Skip whitespace and comments in an extern rust block."""
    while cursor < len(text):
        if text[cursor].isspace():
            cursor += 1
            continue
        if text.startswith("//", cursor):
            newline = text.find("\n", cursor + 2)
            return len(text) if newline == -1 else _skip_extern_ws(text, newline + 1)
        if text.startswith("/*", cursor):
            end = text.find("*/", cursor + 2)
            if end == -1:
                raise ZincModuleError("unterminated comment in extern rust block")
            cursor = end + 2
            continue
        break
    return cursor


def _body_startswith_kw(text: str, cursor: int, keyword: str) -> bool:
    """Return True when text starts with a whole keyword at cursor."""
    if not text.startswith(keyword, cursor):
        return False
    end = cursor + len(keyword)
    return end >= len(text) or not (text[end].isalnum() or text[end] == "_")


def _read_semicolon_item(text: str, cursor: int) -> tuple[str, int]:
    """Read one top-level semicolon-terminated extern item."""
    depth = 0
    i = cursor
    while i < len(text):
        char = text[i]
        if char in "({[":
            depth += 1
        elif char in ")}]":
            depth -= 1
        elif char == ";" and depth == 0:
            return text[cursor : i + 1], i + 1
        i += 1
    raise ZincModuleError("unterminated extern rust item")


def _parse_rust_extern_impl(text: str, cursor: int) -> tuple[list[RustExternFunction], int]:
    """Parse an extern impl block."""
    match = re.match(r"impl\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{", text[cursor:])
    if match is None:
        raise ZincModuleError(f"invalid extern rust impl near: {text[cursor:cursor + 40].strip()}")
    owner_type = match.group(1)
    open_brace = cursor + match.end() - 1
    close_brace = _find_matching_brace(text, open_brace)
    if close_brace is None:
        raise ZincModuleError(f"unterminated extern rust impl for '{owner_type}'")
    body = text[open_brace + 1 : close_brace]
    functions: list[RustExternFunction] = []
    inner_cursor = 0
    while inner_cursor < len(body):
        inner_cursor = _skip_extern_ws(body, inner_cursor)
        if inner_cursor >= len(body):
            break
        if not (_body_startswith_kw(body, inner_cursor, "fn") or _body_startswith_kw(body, inner_cursor, "async")):
            raise ZincModuleError(f"unsupported extern rust impl item near: {body[inner_cursor:inner_cursor + 40].strip()}")
        statement, inner_cursor = _read_semicolon_item(body, inner_cursor)
        function = _parse_rust_extern_function(statement, owner_type=owner_type)
        functions.append(function)
    return functions, close_brace + 1


def _parse_rust_extern_function(statement: str, owner_type: str | None = None) -> RustExternFunction:
    """Parse a Rust extern function signature."""
    text = statement.strip()
    if not text.endswith(";"):
        raise ZincModuleError(f"extern rust function must end with ';': {text}")
    text = text[:-1].strip()
    is_async = False
    if text.startswith("async "):
        is_async = True
        text = text[len("async ") :].lstrip()
    match = re.match(r"fn\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", text)
    if match is None:
        raise ZincModuleError(f"invalid extern rust function declaration: {statement.strip()}")
    name = match.group(1)
    open_paren = match.end() - 1
    close_paren = _find_matching_paren(text, open_paren)
    if close_paren is None:
        raise ZincModuleError(f"unterminated parameter list for extern rust function '{name}'")
    params_text = text[open_paren + 1 : close_paren].strip()
    rest = text[close_paren + 1 :].strip()
    return_type = None
    if rest:
        if not rest.startswith("->"):
            raise ZincModuleError(f"invalid extern rust return annotation for function '{name}'")
        return_type = rest[2:].strip()
        if not return_type:
            raise ZincModuleError(f"missing extern rust return type for function '{name}'")
    params = tuple(_parse_rust_extern_params(params_text))
    is_static = not params or not params[0].is_self
    visible_params = params[1:] if owner_type is not None and params and params[0].is_self else params
    return RustExternFunction(
        name=name,
        params=tuple(visible_params),
        return_type=return_type,
        is_async=is_async,
        owner_type=owner_type,
        is_static=is_static,
        display_name=f"{owner_type}.{name}" if owner_type else name,
    )


def _find_matching_paren(text: str, open_index: int) -> int | None:
    """Find a matching parenthesis in a signature string."""
    depth = 0
    for i in range(open_index, len(text)):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return i
    return None


def _parse_rust_extern_params(params_text: str) -> list[RustExternParameter]:
    """Parse extern function parameters."""
    if not params_text:
        return []
    params: list[RustExternParameter] = []
    for raw_param in _split_top_level_commas(params_text):
        param = raw_param.strip()
        if not param:
            continue
        if param == "self":
            params.append(RustExternParameter(name="self", is_self=True))
            continue
        name, separator, type_text = param.partition(":")
        if separator != ":" or not name.strip() or not type_text.strip():
            raise ZincModuleError(f"invalid extern rust parameter '{param}'")
        params.append(RustExternParameter(name=name.strip(), type_text=type_text.strip()))
    return params


def _split_top_level_commas(text: str) -> list[str]:
    """Split a comma-delimited string while respecting nested type syntax."""
    parts: list[str] = []
    depth = 0
    start = 0
    for i, char in enumerate(text):
        if char in "([{<":
            depth += 1
        elif char in ")]}>":
            depth -= 1
        elif char == "," and depth == 0:
            parts.append(text[start:i])
            start = i + 1
    parts.append(text[start:])
    return parts


def _rust_use_imports_name(statement: str, name: str) -> bool:
    """Best-effort check for whether a Rust use statement imports a visible name."""
    text = statement.strip()
    if text.startswith("use "):
        text = text[len("use ") :].strip()
    if text.endswith(";"):
        text = text[:-1].strip()
    if "::{" in text and text.endswith("}"):
        inner = text[text.rfind("{") + 1 : -1]
        for item in _split_top_level_commas(inner):
            imported = item.strip()
            alias_match = re.search(r"\bas\s+([A-Za-z_][A-Za-z0-9_]*)$", imported)
            if alias_match:
                if alias_match.group(1) == name:
                    return True
                continue
            if imported.rsplit("::", 1)[-1].strip() == name:
                return True
        return False
    alias_match = re.search(r"\bas\s+([A-Za-z_][A-Za-z0-9_]*)$", text)
    if alias_match:
        return alias_match.group(1) == name
    return text.rsplit("::", 1)[-1].strip() == name


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
        elif stmt.asyncFunctionDeclaration():
            ctx = stmt.asyncFunctionDeclaration()
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
        elif stmt.enumDeclaration():
            ctx = stmt.enumDeclaration()
            name = ctx.IDENTIFIER().getText()
            symbol = TopLevelSymbol(
                qualified_name=ModuleGraph.qualified_name(module_id, name),
                module_id=module_id,
                name=name,
                kind="enum",
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
        if symbol.name in RESERVED_ERROR_NAMES:
            raise ZincModuleError(f"'{symbol.name}' is a reserved builtin name")
        if symbol.name in symbols:
            raise ZincModuleError(f"duplicate top-level declaration '{symbol.name}' in module '{module_id}'")
        symbols[symbol.name] = symbol

    return symbols


def _resolve_module_import_scope(graph: ModuleGraph, module: LoadedModule) -> None:
    """Resolve and validate a module's import scope."""
    injected: dict[str, str] = {}
    aliases: dict[str, str] = {}
    local_names = set(module.symbols.keys())
    extern_names = set(module.rust_extern_types.keys()) | set(module.rust_extern_functions.keys())

    for name in extern_names:
        if name in RESERVED_ERROR_NAMES:
            raise ZincModuleError(f"'{name}' is a reserved builtin name")
        if name in local_names:
            raise ZincModuleError(f"extern rust name '{name}' conflicts with a local declaration in module '{module.module_id}'")

    for function in module.rust_extern_methods.values():
        if function.owner_type not in module.rust_extern_types:
            raise ZincModuleError(f"extern rust impl references unknown type '{function.owner_type}'")

    for import_spec in module.imports:
        target = graph.get_module(import_spec.module_path)

        if import_spec.alias:
            alias = import_spec.alias
            if alias in RESERVED_ERROR_NAMES:
                raise ZincModuleError(f"'{alias}' is a reserved builtin name")
            if alias in aliases:
                raise ZincModuleError(f"duplicate import alias '{alias}' in module '{module.module_id}'")
            if alias in injected or alias in local_names or alias in extern_names:
                raise ZincModuleError(f"alias '{alias}' conflicts with an existing name in module '{module.module_id}'")
            aliases[alias] = target.module_id
            continue

        import_names = import_spec.names or tuple(target.exports.keys())
        for name in import_names:
            if name in RESERVED_ERROR_NAMES:
                raise ZincModuleError(f"'{name}' is a reserved builtin name")
            export = target.exports.get(name)
            if export is None:
                raise ZincModuleError(f"module '{target.module_id}' does not export '{name}'")
            if name in local_names or name in extern_names:
                raise ZincModuleError(f"imported name '{name}' conflicts with a local declaration in module '{module.module_id}'")
            if name in injected and injected[name] != export.qualified_name:
                raise ZincModuleError(f"duplicate imported name '{name}' in module '{module.module_id}'")
            injected[name] = export.qualified_name

    module.injected_symbols = injected
    module.alias_imports = aliases
