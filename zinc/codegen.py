"""Code generation for the Zinc compiler."""

import re
from dataclasses import dataclass, field

from antlr4 import ParserRuleContext

from zinc.parser.zincVisitor import zincVisitor
from zinc.parser.zincParser import zincParser as ZincParser
from zinc.atlas import Atlas, FunctionInstance, StructInstance, ConstInstance, StructFieldInfo, StructMethodInfo
from zinc.symbols import SymbolTable, SymbolKind
from zinc.ast.types import (
    ArrayTypeInfo,
    BaseType,
    CallableTarget,
    CallableTypeInfo,
    ChannelTypeInfo,
    DictTypeInfo,
    SetTypeInfo,
    TupleTypeInfo,
    type_to_rust,
)
from zinc.modules import extract_identifier_path, struct_path_from_ctx


@dataclass
class RustProgram:
    """Structured Rust output that can be rendered to a string."""

    imports: list[str] = field(default_factory=list)
    consts: list[str] = field(default_factory=list)
    structs: list[str] = field(default_factory=list)
    functions: list[str] = field(default_factory=list)
    main_body: list[str] = field(default_factory=list)
    uses_async: bool = False

    def render(self) -> str:
        """Assemble final Rust code."""
        parts = []

        if self.imports:
            parts.extend(self.imports)
            parts.append("")

        if self.consts:
            parts.extend(self.consts)
            parts.append("")

        if self.structs:
            for struct in self.structs:
                parts.append(struct)
                parts.append("")

        if self.functions:
            for func in self.functions:
                parts.append(func)
                parts.append("")

        if self.uses_async:
            parts.append("#[tokio::main]")
            parts.append("async fn main() {")
        else:
            parts.append("fn main() {")

        for stmt in self.main_body:
            # Handle multiline statements by indenting each line
            for line in stmt.split("\n"):
                parts.append(f"    {line}")
        parts.append("}")

        return "\n".join(parts)


class CodeGenVisitor(zincVisitor):
    """Generates Rust code from Atlas + SymbolTable."""

    def __init__(
        self,
        atlas: Atlas,
        symbols: SymbolTable,
        specialization_map: dict[tuple[str | None, tuple[int, int]], str] | None = None,
        channel_infos: dict[str, ChannelTypeInfo] | None = None,
    ):
        self.atlas = atlas
        self.module_graph = atlas.module_graph
        self.symbols = symbols
        self._specialization_map = specialization_map or {}  # (caller, interval) -> mangled
        self._channel_infos = channel_infos or {}  # var_name -> ChannelTypeInfo
        self._uses_async = False
        self._current_function: str | None = None
        self._current_module: str | None = None
        self._declared_vars: set[str] = set()
        self._indent_level = 0
        # Struct tracking
        self._struct_instance_vars: dict[str, str] = {}  # var_name -> struct_name
        self._mut_struct_vars: set[str] = set()  # vars that need `let mut`
        self._current_struct: str | None = None  # When generating struct method
        self._current_struct_fields: dict[str, StructFieldInfo] | None = None
        self._current_constructor_owner: str | None = None
        # Track variables that hold compile-time literal values
        self._literal_vars: set[str] = set()
        self._expected_dict_info: DictTypeInfo | None = None
        self._expected_set_info: SetTypeInfo | None = None
        self._expected_tuple_info: TupleTypeInfo | None = None
        self._spawn_handles_var: str | None = None
        self._select_counter = 0
        self._current_channel_params: set[str] = set()
        self._boxed_struct_vars: set[tuple[str | None, str]] = set()
        self._callable_signatures: dict[str, CallableTypeInfo] = {}

    def generate(self) -> RustProgram:
        """Main entry point - generate Rust code for all reachable code."""
        # Pre-scan to determine which struct vars need mut
        self._prescan_for_mut_vars()
        self._collect_callable_signatures()
        self._mark_async_functions()

        imports = self._generate_imports()
        consts = [self._generate_const(c) for c in self.atlas.consts.values()]
        callable_enums = [
            self._generate_callable_enum(info)
            for _, info in sorted(self._callable_signatures.items())
        ]
        structs = [*callable_enums, *[self._generate_struct(s) for s in self.atlas.structs.values()]]
        functions = []
        main_body = []

        for func_name in self.atlas.topological_order():
            func = self.atlas.functions[func_name]
            if func.name == "main":
                self._current_function = func.mangled_name
                self._current_module = func.module_id
                self._declared_vars.clear()
                self._current_channel_params = set()
                main_body = self._generate_function_body(func)
            else:
                functions.append(self._generate_function(func))

        return RustProgram(
            imports=imports,
            consts=consts,
            structs=structs,
            functions=functions,
            main_body=main_body,
            uses_async=self._uses_async,
        )

    def _prescan_for_mut_vars(self) -> None:
        """Scan all code to find struct variables that call &mut self methods."""
        previous_module = self._current_module
        previous_function = self._current_function
        for func in self.atlas.functions.values():
            self._current_module = func.module_id
            self._current_function = func.mangled_name
            if hasattr(func.ctx, "block"):
                self._prescan_block(func.ctx.block())
        self._current_module = previous_module
        self._current_function = previous_function

    def _prescan_block(self, block_ctx) -> None:
        """Recursively scan a block for struct assignments and method calls."""
        for stmt_ctx in block_ctx.statement():
            self._prescan_statement(stmt_ctx)

    def _prescan_statement(self, stmt_ctx) -> None:
        """Scan a statement for struct tracking and literal variable tracking."""
        # Track variable assignments of struct instances and literal values
        if stmt_ctx.variableAssignment():
            var_ctx = stmt_ctx.variableAssignment()
            target = var_ctx.assignmentTarget()
            if target.IDENTIFIER():
                var_name = target.IDENTIFIER().getText()
                expr = var_ctx.expression()
                struct_name = self._detect_struct_assignment(expr)
                if struct_name:
                    self._struct_instance_vars[f"{self._current_function}:{var_name}"] = struct_name
                # Track if variable is assigned a compile-time literal value
                elif self._is_compile_time_literal_expr(expr):
                    self._literal_vars.add(var_name)

        self._prescan_callable_escapes(stmt_ctx)

        # Track method calls that require mut
        if stmt_ctx.expressionStatement():
            expr = stmt_ctx.expressionStatement().expression()
            self._check_for_mut_method_call(expr)

        # Recurse into blocks
        if stmt_ctx.ifStatement():
            for block in stmt_ctx.ifStatement().block():
                self._prescan_block(block)
        if stmt_ctx.forStatement():
            self._prescan_block(stmt_ctx.forStatement().block())
        if stmt_ctx.whileStatement():
            self._prescan_block(stmt_ctx.whileStatement().block())
        if stmt_ctx.loopStatement():
            self._prescan_block(stmt_ctx.loopStatement().block())

    def _prescan_callable_escapes(self, node) -> None:
        """Collect struct receivers whose bound methods escape as callable values."""
        if node is None:
            return
        if isinstance(node, ZincParser.MemberAccessExprContext) and self._current_function is not None:
            parent = node.parentCtx
            is_direct_call = (
                isinstance(parent, ZincParser.FunctionCallExprContext)
                and parent.expression() is node
            )
            if not is_direct_call:
                symbol = self.symbols.lookup_by_interval(
                    node.getSourceInterval(), self._current_function
                )
                if symbol and symbol.callable_info:
                    for target in symbol.callable_info.targets:
                        if target.kind == "bound_method" and target.receiver_name:
                            self._boxed_struct_vars.add((self._current_function, target.receiver_name))
        if hasattr(node, "getChildCount"):
            for i in range(node.getChildCount()):
                child = node.getChild(i)
                if isinstance(child, ParserRuleContext):
                    self._prescan_callable_escapes(child)

    def _detect_struct_assignment(self, expr_ctx) -> str | None:
        """Detect if expression assigns a struct instance, return struct name."""
        # Direct struct instantiation: Point { x: 1, y: 2 }
        if isinstance(expr_ctx, ZincParser.PrimaryExprContext):
            primary = expr_ctx.primaryExpression()
            if primary and primary.structInstantiation():
                if self._current_module is not None:
                    struct_symbol = self.module_graph.resolve_struct_path(
                        self._current_module, struct_path_from_ctx(primary.structInstantiation())
                    )
                    if struct_symbol:
                        return struct_symbol.qualified_name

        # Static method call returning Self: Counter.new(0)
        if isinstance(expr_ctx, ZincParser.FunctionCallExprContext):
            path = extract_identifier_path(expr_ctx.expression())
            if path and self._current_module is not None:
                static_target = self.module_graph.resolve_static_method_target(self._current_module, path)
                if static_target:
                    struct_symbol, method_name = static_target
                    struct = self.atlas.structs.get(struct_symbol.qualified_name)
                    if struct:
                        method = next((m for m in struct.methods if m.name == method_name), None)
                        if method and method.return_type == "Self":
                            return struct_symbol.qualified_name
        return None

    def _check_for_mut_method_call(self, expr_ctx) -> None:
        """Check if expression is a method call requiring &mut self."""
        if isinstance(expr_ctx, ZincParser.FunctionCallExprContext):
            callee = expr_ctx.expression()
            if isinstance(callee, ZincParser.MemberAccessExprContext):
                target_ctx = callee.expression()
                method_name = callee.IDENTIFIER().getText()

                # Get target variable name
                if isinstance(target_ctx, ZincParser.PrimaryExprContext):
                    primary = target_ctx.primaryExpression()
                    if primary and primary.IDENTIFIER():
                        target_text = primary.IDENTIFIER().getText()
                        key = f"{self._current_function}:{target_text}"
                        if key in self._struct_instance_vars:
                            struct_name = self._struct_instance_vars[key]
                            struct = self.atlas.structs.get(struct_name)
                            if struct:
                                method = next((m for m in struct.methods if m.name == method_name), None)
                                if method and method.self_mutability == "&mut self":
                                    self._mut_struct_vars.add(target_text)

    def _node_requires_async(self, node, function_name: str | None) -> bool:
        """Return True when a parse subtree requires async Rust lowering."""
        if isinstance(node, ZincParser.SelectStatementContext):
            return True
        if isinstance(node, ZincParser.ChannelReceiveExprContext):
            return True
        if isinstance(node, ZincParser.AwaitExprContext):
            return True
        if isinstance(node, ZincParser.ChannelSendStatementContext):
            chan_info = self._channel_infos.get(node.IDENTIFIER().getText())
            return bool(chan_info and chan_info.is_bounded)
        if isinstance(node, ZincParser.FunctionCallExprContext):
            key = (function_name, node.getSourceInterval())
            mangled = self._specialization_map.get(key)
            if mangled and mangled in self.atlas.functions and self.atlas.functions[mangled].is_async:
                return True

        if isinstance(node, ParserRuleContext):
            for i in range(node.getChildCount()):
                child = node.getChild(i)
                if isinstance(child, ParserRuleContext) and self._node_requires_async(child, function_name):
                    return True
        return False

    def _channel_sender_expr(self, name: str, clone: bool = False) -> str:
        """Render the Rust sender endpoint for a Zinc channel value."""
        if name in self._current_channel_params:
            base = name
        elif name in self._channel_infos:
            base = f"{name}_tx"
        else:
            base = name
        return f"{base}.clone()" if clone else base

    def _channel_receiver_expr(self, name: str) -> str:
        """Render the Rust receiver endpoint for a Zinc channel value."""
        if name in self._current_channel_params:
            return name
        if name in self._channel_infos:
            return f"{name}_rx"
        return name

    def _render_channel_value(self, channel_name: str, expr_ctx) -> str:
        """Render a channel payload with the channel element type's ownership rules."""
        value = self.visit(expr_ctx)
        chan_info = self._channel_infos.get(channel_name)
        target_type = chan_info.element_type if chan_info else self._get_expr_type(expr_ctx)
        return self._coerce_owned(value, target_type, expr_ctx)

    def _render_scoped_block(self, block_ctx, prelude: list[str] | None = None, local_names: set[str] | None = None) -> list[str]:
        """Render a block while keeping block-local declarations out of outer scopes."""
        previous_declared = set(self._declared_vars)
        if local_names:
            self._declared_vars.update(local_names)
        try:
            body = self._generate_block(block_ctx)
        finally:
            self._declared_vars = previous_declared
        if prelude:
            return [*prelude, *body]
        return body

    def _append_block_lines(self, lines: list[str], stmts: list[str], indent: int) -> None:
        """Append rendered statements with a fixed indentation level."""
        prefix = "    " * indent
        for stmt in stmts:
            for line in stmt.split("\n"):
                lines.append(f"{prefix}{line}")

    def _generate_imports(self) -> list[str]:
        """Generate import statements based on what's used."""
        imports = []
        collections: set[str] = set()
        needs_rc_refcell = bool(self._boxed_struct_vars)
        for symbol in self.symbols.all_symbols():
            if symbol.dict_info:
                collections.add(symbol.dict_info.rust_container())
            if symbol.set_info:
                collections.add(symbol.set_info.rust_container())
        for info in self._callable_signatures.values():
            for dict_info in info.param_dict_infos.values():
                collections.add(dict_info.rust_container())
            for set_info in info.param_set_infos.values():
                collections.add(set_info.rust_container())
            if info.return_dict_info:
                collections.add(info.return_dict_info.rust_container())
            if info.return_set_info:
                collections.add(info.return_set_info.rust_container())
        if collections:
            imports.append(f"use std::collections::{{{', '.join(sorted(collections))}}};")
        if needs_rc_refcell:
            imports.append("use std::cell::RefCell;")
            imports.append("use std::rc::Rc;")
        return imports

    def _register_callable_info(self, info: CallableTypeInfo | None) -> None:
        """Collect a concrete callable signature and all nested callable signatures."""
        if info is None:
            return
        key = info.rust_type_name()
        existing = self._callable_signatures.get(key)
        if existing is None:
            self._callable_signatures[key] = info.copy()
        else:
            self._callable_signatures[key] = existing.merge_targets_from(info)

        for nested in info.param_callable_infos.values():
            self._register_callable_info(nested)
        self._register_callable_info(info.return_callable_info)
        for array_info in info.param_array_infos.values():
            self._register_callable_info(array_info.element_callable_info)
        for dict_info in info.param_dict_infos.values():
            self._register_callable_info(dict_info.key_callable_info)
            self._register_callable_info(dict_info.value_callable_info)
        for tuple_info in info.param_tuple_infos.values():
            for nested in tuple_info.element_callable_infos.values():
                self._register_callable_info(nested)
        if info.return_dict_info:
            self._register_callable_info(info.return_dict_info.key_callable_info)
            self._register_callable_info(info.return_dict_info.value_callable_info)
        if info.return_tuple_info:
            for nested in info.return_tuple_info.element_callable_infos.values():
                self._register_callable_info(nested)

    def _collect_callable_signatures(self) -> None:
        """Collect every callable signature that needs a Rust enum."""
        self._callable_signatures = {}
        for struct in self.atlas.structs.values():
            for field in struct.fields:
                self._register_callable_info(field.callable_info)
        for func in self.atlas.functions.values():
            for info in func.arg_callable_infos.values():
                self._register_callable_info(info)
            self._register_callable_info(func.return_callable_info)
        for symbol in self.symbols.all_symbols():
            if symbol.kind not in {SymbolKind.VARIABLE, SymbolKind.PARAMETER}:
                continue
            self._register_callable_info(symbol.callable_info)
            if symbol.dict_info:
                self._register_callable_info(symbol.dict_info.key_callable_info)
                self._register_callable_info(symbol.dict_info.value_callable_info)
            if symbol.tuple_info:
                for nested in symbol.tuple_info.element_callable_infos.values():
                    self._register_callable_info(nested)
        self._prune_abstract_callable_signatures()

    def _prune_abstract_callable_signatures(self) -> None:
        """Drop abstract callable signatures when a concrete version exists for the same target set."""
        grouped: dict[tuple[tuple, int], list[CallableTypeInfo]] = {}
        for info in self._callable_signatures.values():
            target_key = tuple(sorted(target.storage_key() for target in info.targets))
            grouped.setdefault((target_key, len(info.param_types)), []).append(info)

        keep: dict[str, CallableTypeInfo] = {}
        for infos in grouped.values():
            has_concrete = any(
                all(base_type != BaseType.UNKNOWN for base_type in info.param_types)
                and info.return_type != BaseType.UNKNOWN
                for info in infos
            )
            for info in infos:
                is_abstract = (
                    any(base_type == BaseType.UNKNOWN for base_type in info.param_types)
                    or info.return_type == BaseType.UNKNOWN
                )
                if is_abstract and has_concrete:
                    continue
                keep[info.rust_type_name()] = info
        self._callable_signatures = keep

    def _callable_variant_name(self, info: CallableTypeInfo, target: CallableTarget) -> str:
        """Return the stable enum variant name for a callable target."""
        registry_info = self._callable_signatures.get(info.rust_type_name(), info)
        ordered = sorted(registry_info.targets, key=lambda item: item.storage_key())
        for index, candidate in enumerate(ordered):
            if candidate.storage_key() == target.storage_key():
                return f"V{index}"
        raise KeyError(f"unknown callable target: {target.display_name}")

    def _type_with_metadata_to_rust(
        self,
        base_type: BaseType,
        *,
        array_info: ArrayTypeInfo | None = None,
        dict_info: DictTypeInfo | None = None,
        set_info: SetTypeInfo | None = None,
        tuple_info: TupleTypeInfo | None = None,
        callable_info: CallableTypeInfo | None = None,
        as_reference: bool = False,
    ) -> str:
        """Render a full Zinc type including rich metadata."""
        if base_type == BaseType.ARRAY and array_info:
            return array_info.to_rust_type(as_reference=as_reference)
        if base_type == BaseType.DICT and dict_info:
            return dict_info.to_rust_type(as_reference=as_reference)
        if base_type == BaseType.SET and set_info:
            return set_info.to_rust_type(as_reference=as_reference)
        if base_type == BaseType.TUPLE and tuple_info:
            return tuple_info.to_rust_type()
        if base_type == BaseType.CALLABLE and callable_info:
            return callable_info.rust_type_name()
        if base_type == BaseType.VOID:
            return "()"
        return type_to_rust(base_type)

    def _callable_param_rust_type(self, info: CallableTypeInfo, index: int) -> str:
        """Render the Rust type for a callable parameter slot."""
        return self._type_with_metadata_to_rust(
            info.param_types[index],
            array_info=info.param_array_infos.get(index),
            dict_info=info.param_dict_infos.get(index),
            set_info=info.param_set_infos.get(index),
            tuple_info=info.param_tuple_infos.get(index),
            callable_info=info.param_callable_infos.get(index),
            as_reference=info.param_types[index] in {BaseType.ARRAY, BaseType.DICT, BaseType.SET},
        )

    def _callable_return_rust_type(self, info: CallableTypeInfo) -> str:
        """Render the Rust return type for a callable signature."""
        return self._type_with_metadata_to_rust(
            info.return_type,
            dict_info=info.return_dict_info,
            set_info=info.return_set_info,
            tuple_info=info.return_tuple_info,
            callable_info=info.return_callable_info,
            as_reference=False,
        )

    def _callable_dispatch_target(self, info: CallableTypeInfo, target: CallableTarget) -> str:
        """Render the Rust callable target for a dispatcher arm."""
        if target.kind in {"function", "lambda"}:
            return self.atlas._mangle_name(
                target.qualified_name,
                info.param_types,
                arg_array_infos=info.param_array_infos,
                arg_dict_infos=info.param_dict_infos,
                arg_set_infos=info.param_set_infos,
                arg_tuple_infos=info.param_tuple_infos,
                arg_callable_infos=info.param_callable_infos,
            )
        if target.kind == "static_method":
            struct_qualified_name = target.receiver_struct_qualified_name or target.qualified_name.rpartition("::")[0]
            method_name = target.qualified_name.rpartition("::")[2]
            struct = self.atlas.structs[struct_qualified_name]
            return f"{self._struct_rust_name(struct)}::{method_name}"
        if target.kind == "bound_method":
            return target.qualified_name.rpartition("::")[2]
        raise KeyError(f"unknown callable target kind: {target.kind}")

    def _callable_variant_payload_type(self, target: CallableTarget) -> str | None:
        """Return the Rust payload type for a callable enum variant."""
        if target.kind != "bound_method":
            return None
        struct_qualified_name = target.receiver_struct_qualified_name
        if struct_qualified_name is None:
            return None
        struct = self.atlas.structs.get(struct_qualified_name)
        if struct is None:
            return None
        return f"Rc<RefCell<{self._struct_rust_name(struct)}>>"

    def _generate_callable_enum(self, info: CallableTypeInfo) -> str:
        """Generate a Rust enum and dispatcher for one callable signature."""
        ordered_targets = sorted(info.targets, key=lambda target: target.storage_key())
        lines = ["#[derive(Clone)]", f"enum {info.rust_type_name()} {{"]
        for target in ordered_targets:
            variant_name = self._callable_variant_name(info, target)
            payload_type = self._callable_variant_payload_type(target)
            if payload_type:
                lines.append(f"    {variant_name}({payload_type}),")
            else:
                lines.append(f"    {variant_name},")
        lines.append("}")
        lines.append("")
        lines.append(f"impl {info.rust_type_name()} {{")
        params = [
            f"arg_{index}: {self._callable_param_rust_type(info, index)}"
            for index in range(len(info.param_types))
        ]
        ret_type = self._callable_return_rust_type(info)
        ret_suffix = "" if ret_type == "()" else f" -> {ret_type}"
        lines.append(f"    fn call(&self, {', '.join(params)}){ret_suffix} {{")
        lines.append("        match self {")
        for target in ordered_targets:
            variant_name = self._callable_variant_name(info, target)
            args = ", ".join(f"arg_{index}" for index in range(len(info.param_types)))
            if target.kind == "bound_method":
                method_name = self._callable_dispatch_target(info, target)
                borrow = "borrow_mut" if target.receiver_mutability == "&mut self" else "borrow"
                call_expr = f"receiver.{borrow}().{method_name}({args})"
                if ret_type == "()":
                    lines.append(f"            Self::{variant_name}(receiver) => {{ {call_expr}; }}")
                else:
                    lines.append(f"            Self::{variant_name}(receiver) => {call_expr},")
            else:
                callee = self._callable_dispatch_target(info, target)
                call_expr = f"{callee}({args})"
                if ret_type == "()":
                    lines.append(f"            Self::{variant_name} => {{ {call_expr}; }}")
                else:
                    lines.append(f"            Self::{variant_name} => {call_expr},")
        lines.append("        }")
        lines.append("    }")
        lines.append("}")
        return "\n".join(lines)

    def _boxed_struct_key(self, name: str) -> tuple[str | None, str]:
        """Return the lookup key for a possibly boxed struct variable."""
        return (self._current_function, name)

    def _render_callable_value(self, info: CallableTypeInfo) -> str:
        """Render a direct callable value expression as an enum constructor."""
        if len(info.targets) != 1:
            raise ValueError("direct callable expressions must resolve to a single target")
        target = info.targets[0]
        variant_name = self._callable_variant_name(info, target)
        if target.kind == "bound_method":
            receiver_name = target.receiver_name or ""
            return f"{info.rust_type_name()}::{variant_name}({receiver_name}.clone())"
        return f"{info.rust_type_name()}::{variant_name}"

    def _render_callable_value_for_signature(
        self,
        info: CallableTypeInfo,
        expected_info: CallableTypeInfo,
    ) -> str:
        """Render a direct callable value using an expected concrete signature."""
        if len(info.targets) != 1:
            raise ValueError("direct callable expressions must resolve to a single target")
        target = info.targets[0]
        variant_name = self._callable_variant_name(expected_info, target)
        if target.kind == "bound_method":
            receiver_name = target.receiver_name or ""
            return f"{expected_info.rust_type_name()}::{variant_name}({receiver_name}.clone())"
        return f"{expected_info.rust_type_name()}::{variant_name}"

    def _process_callable_args(
        self,
        callable_info: CallableTypeInfo,
        args: list[str],
        arg_ctxs: list | None = None,
    ) -> list[str]:
        """Process indirect-call arguments using a callable signature."""
        processed: list[str] = []
        for i, arg in enumerate(args):
            if i < len(callable_info.param_types):
                param_type = callable_info.param_types[i]
                if param_type == BaseType.STRING and arg.startswith('"'):
                    processed.append(f"String::from({arg})")
                elif param_type == BaseType.ARRAY and i in callable_info.param_array_infos:
                    arr_info = callable_info.param_array_infos[i]
                    processed.append(f"&mut {arg}" if arr_info.is_mutated else f"&{arg}")
                elif param_type == BaseType.DICT and i in callable_info.param_dict_infos:
                    dict_info = callable_info.param_dict_infos[i]
                    processed.append(f"&mut {arg}" if dict_info.is_mutated else f"&{arg}")
                elif param_type == BaseType.SET and i in callable_info.param_set_infos:
                    set_info = callable_info.param_set_infos[i]
                    processed.append(f"&mut {arg}" if set_info.is_mutated else f"&{arg}")
                elif param_type == BaseType.CALLABLE and i in callable_info.param_callable_infos:
                    arg_ctx = arg_ctxs[i] if arg_ctxs and i < len(arg_ctxs) else None
                    arg_symbol = self._get_expr_symbol(arg_ctx) if arg_ctx is not None else None
                    is_local_callable = (
                        isinstance(arg_ctx, ZincParser.PrimaryExprContext)
                        and arg_ctx.primaryExpression()
                        and arg_ctx.primaryExpression().IDENTIFIER()
                        and arg_ctx.primaryExpression().IDENTIFIER().getText() in self._declared_vars
                    )
                    if arg_symbol and arg_symbol.callable_info and not is_local_callable:
                        processed.append(
                            self._render_callable_value_for_signature(
                                arg_symbol.callable_info,
                                callable_info.param_callable_infos[i],
                            )
                        )
                    else:
                        processed.append(f"{arg}.clone()")
                else:
                    processed.append(arg)
            else:
                processed.append(arg)
        return processed

    def _mark_async_functions(self) -> None:
        """Mark functions that need async because they spawn or call async functions."""
        async_funcs = {
            name
            for name, func in self.atlas.functions.items()
            if func.is_async or self._node_requires_async(func.ctx.block(), name)
        }

        changed = True
        while changed:
            changed = False
            for caller, callees in self.atlas.calls.items():
                if caller in self.atlas.functions and any(callee in async_funcs for callee in callees):
                    if caller not in async_funcs:
                        async_funcs.add(caller)
                        changed = True

        for name in async_funcs:
            if name in self.atlas.functions and self.atlas.functions[name].name == "main":
                self._uses_async = True
            elif name in self.atlas.functions:
                self.atlas.functions[name].is_async = True

    def _struct_rust_name(self, struct: StructInstance) -> str:
        """Return the flattened Rust name for a struct."""
        return self.module_graph.rust_base_name(struct.qualified_name)

    def _const_rust_name(self, const: ConstInstance) -> str:
        """Return the flattened Rust name for a const."""
        return self.module_graph.rust_base_name(const.qualified_name).upper()

    def _const_symbol(self, const: ConstInstance):
        """Return the resolved symbol-table entry for a const, if any."""
        return self.symbols.lookup_by_id(const.qualified_name)

    def _const_expr(self, const: ConstInstance) -> str:
        """Return a Rust expression that evaluates to the Zinc const's value."""
        symbol = self._const_symbol(const)
        rust_name = self._const_rust_name(const)
        if symbol and symbol.resolved_type == BaseType.STRING:
            return f"(*{rust_name}).clone()"
        return rust_name

    def _struct_rust_name_from_symbol(self, symbol) -> str:
        """Return the flattened Rust name for a resolved struct symbol."""
        return self.module_graph.rust_base_name(symbol.qualified_name)

    def _generate_const(self, const: ConstInstance) -> str:
        """Generate a const declaration."""
        ctx: ZincParser.ConstDeclarationContext = const.ctx
        previous_module = self._current_module
        self._current_module = const.module_id
        try:
            value = self.visit(ctx.expression())
        finally:
            self._current_module = previous_module
        name = self._const_rust_name(const)
        symbol = self._const_symbol(const)
        if symbol:
            type_str = type_to_rust(symbol.resolved_type)
            if type_str == "String":
                if value.startswith('"'):
                    value = f"String::from({value})"
                return f"static {name}: std::sync::LazyLock<String> = std::sync::LazyLock::new(|| {value});"
            return f"const {name}: {type_str} = {value};"
        return f"const {name} = {value};"

    def _generate_struct(self, struct: StructInstance) -> str:
        """Generate a struct definition and impl block."""
        lines = []
        rust_name = self._struct_rust_name(struct)

        # Struct definition
        lines.append(f"struct {rust_name} {{")
        for f in struct.fields:
            vis = "" if f.is_private else "pub "
            rust_type = f.rust_type()
            lines.append(f"    {vis}{f.name}: {rust_type},")
        lines.append("}")

        # Impl block (only if there are methods)
        if struct.methods:
            lines.append("")
            lines.append(f"impl {rust_name} {{")
            for method in struct.methods:
                method_code = self._generate_struct_method(method, struct)
                for line in method_code.split("\n"):
                    lines.append(f"    {line}")
            lines.append("}")

        return "\n".join(lines)

    def _generate_struct_method(self, method: StructMethodInfo, struct: StructInstance) -> str:
        """Generate a single struct method."""
        previous_declared = self._declared_vars.copy()
        self._declared_vars = {name for name, _, _ in method.parameters}
        if not method.is_static:
            self._declared_vars.add("self")

        # Build parameter list
        param_strs = []
        if not method.is_static:
            param_strs.append(method.self_mutability or "&self")

        for name, type_ann, resolved in method.parameters:
            if type_ann:
                param_strs.append(f"{name}: {self._zinc_type_to_rust(type_ann)}")
            elif resolved:
                param_strs.append(f"{name}: {resolved}")
            else:
                param_strs.append(f"{name}: i64")  # Default fallback

        params = ", ".join(param_strs)
        ret_type = f" -> {method.return_type}" if method.return_type else ""

        # Generate body
        previous_module = self._current_module
        previous_constructor_owner = self._current_constructor_owner
        self._current_module = struct.module_id
        if method.source_module_id is not None:
            self._current_module = method.source_module_id
        self._current_struct = struct.qualified_name
        self._current_struct_fields = {f.name: f for f in struct.fields}
        self._current_constructor_owner = (
            method.constructor_owner_qualified_name or method.source_struct_qualified_name
        )
        body_stmts = self._generate_block(method.body_ctx)
        self._current_struct = None
        self._current_struct_fields = None
        self._current_constructor_owner = previous_constructor_owner
        self._current_module = previous_module
        self._declared_vars = previous_declared

        lines = [f"fn {method.name}({params}){ret_type} {{"]
        for stmt in body_stmts:
            for line in stmt.split("\n"):
                lines.append(f"    {line}")
        lines.append("}")

        return "\n".join(lines)

    def _zinc_type_to_rust(self, zinc_type: str) -> str:
        """Convert Zinc type annotation to Rust type."""
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
        return mapping.get(zinc_type.lower(), zinc_type)

    def _generate_function(self, func: FunctionInstance) -> str:
        """Generate a function definition using mangled name."""
        self._current_function = func.mangled_name
        self._current_module = func.module_id
        self._declared_vars.clear()
        self._current_channel_params = set()
        ctx: ZincParser.FunctionDeclarationContext = func.ctx

        # Get parameter names and types from func.arg_types
        params = []
        if ctx.parameterList():
            for i, param_ctx in enumerate(ctx.parameterList().parameter()):
                param_name = param_ctx.IDENTIFIER().getText()
                if i < len(func.arg_types):
                    # Check if this is a channel parameter with type info
                    if i in func.arg_channel_infos and func.arg_channel_infos[i]:
                        # Use first channel info (all should have same element type)
                        chan_info = func.arg_channel_infos[i][0]
                        type_str = chan_info.to_rust_sender()
                        self._current_channel_params.add(param_name)
                    # Check if this is an array parameter with element type info
                    elif i in func.arg_array_infos:
                        arr_info = func.arg_array_infos[i]
                        type_str = arr_info.to_rust_type()
                    elif i in func.arg_dict_infos:
                        dict_info = func.arg_dict_infos[i]
                        type_str = dict_info.to_rust_type()
                    elif i in func.arg_set_infos:
                        set_info = func.arg_set_infos[i]
                        type_str = set_info.to_rust_type()
                    elif i in func.arg_tuple_infos:
                        tuple_info = func.arg_tuple_infos[i]
                        type_str = tuple_info.to_rust_type()
                    elif i in func.arg_callable_infos:
                        type_str = func.arg_callable_infos[i].rust_type_name()
                    else:
                        type_str = type_to_rust(func.arg_types[i])
                    params.append(f"{param_name}: {type_str}")
                else:
                    params.append(param_name)
                self._declared_vars.add(param_name)

        body_stmts = self._generate_function_body(func)
        param_str = ", ".join(params)

        # Build return type suffix if not void
        if func.return_type != BaseType.VOID:
            if func.return_type == BaseType.DICT and func.return_dict_info:
                return_type_str = f" -> {func.return_dict_info.to_rust_type(as_reference=False)}"
            elif func.return_type == BaseType.SET and func.return_set_info:
                return_type_str = f" -> {func.return_set_info.to_rust_type(as_reference=False)}"
            elif func.return_type == BaseType.TUPLE and func.return_tuple_info:
                return_type_str = f" -> {func.return_tuple_info.to_rust_type()}"
            elif func.return_type == BaseType.CALLABLE and func.return_callable_info:
                return_type_str = f" -> {func.return_callable_info.rust_type_name()}"
            else:
                return_type_str = f" -> {type_to_rust(func.return_type)}"
        else:
            return_type_str = ""

        # Use mangled_name for the Rust function name
        async_kw = "async " if func.is_async else ""
        lines = [f"{async_kw}fn {func.mangled_name}({param_str}){return_type_str} {{"]
        for stmt in body_stmts:
            # Handle multiline statements (like for loops, if/else) by indenting each line
            for line in stmt.split("\n"):
                lines.append(f"    {line}")
        lines.append("}")

        return "\n".join(lines)

    def _generate_function_body(self, func: FunctionInstance) -> list[str]:
        """Generate statements for a function body."""
        ctx: ZincParser.FunctionDeclarationContext = func.ctx
        has_spawns = self._block_contains_spawn(ctx.block())
        previous_spawn_handles_var = self._spawn_handles_var
        self._spawn_handles_var = "__zinc_spawn_handles" if has_spawns else None
        try:
            body = self._generate_block(ctx.block())
        finally:
            self._spawn_handles_var = previous_spawn_handles_var

        if not has_spawns:
            return body

        body_with_setup = [
            "let mut __zinc_spawn_handles = Vec::new();",
            *body,
        ]
        if func.return_type == BaseType.VOID:
            body_with_setup.append(self._render_spawn_handle_awaits("__zinc_spawn_handles"))
        return body_with_setup

    def _block_contains_spawn(self, ctx: ZincParser.BlockContext) -> bool:
        """Return True if a block contains any spawn statement."""
        for stmt in ctx.statement():
            if stmt.spawnStatement():
                return True
            if stmt.ifStatement():
                if any(self._block_contains_spawn(block) for block in stmt.ifStatement().block()):
                    return True
            if stmt.forStatement() and self._block_contains_spawn(stmt.forStatement().block()):
                return True
            if stmt.whileStatement() and self._block_contains_spawn(stmt.whileStatement().block()):
                return True
            if stmt.loopStatement() and self._block_contains_spawn(stmt.loopStatement().block()):
                return True
        return False

    def _render_spawn_handle_awaits(self, handle_var: str) -> str:
        """Render code that waits for all spawned tasks in this function."""
        return "\n".join([
            f"while let Some(__zinc_spawn_handle) = {handle_var}.pop() {{",
            "    __zinc_spawn_handle.await.unwrap();",
            "}",
        ])

    def _generate_block(self, ctx: ZincParser.BlockContext) -> list[str]:
        """Generate statements for a block."""
        stmts = []
        for stmt_ctx in ctx.statement():
            result = self.visit(stmt_ctx)
            if result:
                if isinstance(result, list):
                    stmts.extend(result)
                else:
                    stmts.append(result)
        return stmts

    def _indent(self, text: str) -> str:
        """Add current indentation to text."""
        indent = "    " * self._indent_level
        return f"{indent}{text}"

    # --- Expression Visitors (return Rust code strings) ---

    def visitLiteral(self, ctx: ZincParser.LiteralContext) -> str:
        """Visit a literal value."""
        text = ctx.getText()
        if text.startswith('"') and "{" in text:
            return self._render_interpolated_string(text)
        return text

    def _render_interpolated_string(self, text: str) -> str:
        """Convert string interpolation to format! macro."""
        inner = text[1:-1]
        interpolations = re.findall(r"\{([^}]+)\}", inner)
        if not interpolations:
            return text
        format_str = re.sub(r"\{[^}]+\}", "{}", inner)
        args = ", ".join(self._rewrite_interpolation_expr(expr) for expr in interpolations)
        return f'format!("{format_str}", {args})'

    def _rewrite_interpolation_expr(self, expr: str) -> str:
        """Rewrite imported const and struct references inside string interpolation."""
        if self._current_module is None:
            return expr

        keyword_like = {"and", "or", "not", "true", "false", "self"}

        def replace(match: re.Match[str]) -> str:
            token = match.group(0)
            if token in keyword_like:
                return token

            parts = token.split(".")
            if len(parts) == 1 and token in self._declared_vars:
                return token

            const_symbol = self.module_graph.resolve_const_path(self._current_module, parts)
            if const_symbol:
                const = self.atlas.consts.get(const_symbol.qualified_name)
                if const:
                    return self._const_expr(const)
                return self.module_graph.rust_base_name(const_symbol.qualified_name).upper()

            struct_symbol = self.module_graph.resolve_struct_path(self._current_module, parts)
            if struct_symbol:
                struct = self.atlas.structs.get(struct_symbol.qualified_name)
                if struct:
                    return self._struct_rust_name(struct)
                return self.module_graph.rust_base_name(struct_symbol.qualified_name)

            static_target = self.module_graph.resolve_static_method_target(self._current_module, parts)
            if static_target:
                struct_symbol, method_name = static_target
                struct = self.atlas.structs.get(struct_symbol.qualified_name)
                if struct:
                    return f"{self._struct_rust_name(struct)}::{method_name}"
                return f"{self.module_graph.rust_base_name(struct_symbol.qualified_name)}::{method_name}"

            return token

        return re.sub(r"\b[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*\b", replace, expr)

    def visitPrimaryExpression(self, ctx: ZincParser.PrimaryExpressionContext) -> str:
        """Visit a primary expression."""
        if ctx.literal():
            return self.visit(ctx.literal())
        if ctx.IDENTIFIER():
            name = ctx.IDENTIFIER().getText()
            expr_symbol = self._get_expr_symbol(ctx)
            is_direct_call = (
                isinstance(ctx.parentCtx, ZincParser.PrimaryExprContext)
                and isinstance(ctx.parentCtx.parentCtx, ZincParser.FunctionCallExprContext)
                and ctx.parentCtx.parentCtx.expression() is ctx.parentCtx
            )
            if (
                expr_symbol
                and expr_symbol.resolved_type == BaseType.CALLABLE
                and name not in self._declared_vars
                and not is_direct_call
            ):
                return self._render_callable_value(expr_symbol.callable_info)
            if self._current_module is not None:
                const_symbol = self.module_graph.resolve_const_path(self._current_module, [name])
                if const_symbol:
                    const = self.atlas.consts.get(const_symbol.qualified_name)
                    if const:
                        return self._const_expr(const)
                    return self.module_graph.rust_base_name(const_symbol.qualified_name).upper()
            return name
        if ctx.arrayLiteral():
            return self.visit(ctx.arrayLiteral())
        if ctx.collectionLiteral():
            return self.visit(ctx.collectionLiteral())
        if ctx.tupleLiteral():
            return self.visit(ctx.tupleLiteral())
        if ctx.structInstantiation():
            return self.visit(ctx.structInstantiation())
        if ctx.getText() == "self":
            return "self"
        if ctx.expression():
            return f"({self.visit(ctx.expression())})"
        return ctx.getText()

    def visitPrimaryExpr(self, ctx: ZincParser.PrimaryExprContext) -> str:
        """Visit primary expression wrapper."""
        return self.visit(ctx.primaryExpression())

    def visitLambdaExpr(self, ctx: ZincParser.LambdaExprContext) -> str:
        """Visit a lambda expression wrapper."""
        return self.visit(ctx.lambdaExpression())

    def visitLambdaExpression(self, ctx: ZincParser.LambdaExpressionContext) -> str:
        """Render a lambda expression as a callable enum constructor."""
        expr_symbol = self._get_expr_symbol(ctx)
        if expr_symbol and expr_symbol.callable_info:
            return self._render_callable_value(expr_symbol.callable_info)
        return "__zinc_lambda_missing"

    def visitParenExpr(self, ctx: ZincParser.ParenExprContext) -> str:
        """Visit parenthesized expression."""
        return f"({self.visit(ctx.expression())})"

    def visitTupleLiteral(self, ctx: ZincParser.TupleLiteralContext) -> str:
        """Visit tuple literal."""
        info = self._expected_tuple_info or self._get_tuple_info(ctx) or TupleTypeInfo()
        elements = []
        for i, expr_ctx in enumerate(ctx.expression()):
            value = self.visit(expr_ctx)
            target_type = info.element_types[i] if i < len(info.element_types) else self._get_expr_type(expr_ctx)
            elements.append(self._coerce_owned(value, target_type, expr_ctx))
        if len(elements) == 1:
            return f"({elements[0]},)"
        return f"({', '.join(elements)})"

    def visitAdditiveExpr(self, ctx: ZincParser.AdditiveExprContext) -> str:
        """Visit addition/subtraction expression."""
        left = self.visit(ctx.expression(0))
        op = ctx.getChild(1).getText()
        right = self.visit(ctx.expression(1))

        # Handle type promotion: int + float -> cast int to f64
        left_type = self._get_expr_type(ctx.expression(0))
        right_type = self._get_expr_type(ctx.expression(1))

        if left_type == BaseType.INTEGER and right_type == BaseType.FLOAT:
            left = f"({left} as f64)"
        elif left_type == BaseType.FLOAT and right_type == BaseType.INTEGER:
            right = f"({right} as f64)"

        return f"({left} {op} {right})"

    def visitMultiplicativeExpr(self, ctx: ZincParser.MultiplicativeExprContext) -> str:
        """Visit multiplication/division expression."""
        left = self.visit(ctx.expression(0))
        op = ctx.getChild(1).getText()
        right = self.visit(ctx.expression(1))

        # Handle type promotion: int * float -> cast int to f64
        left_type = self._get_expr_type(ctx.expression(0))
        right_type = self._get_expr_type(ctx.expression(1))

        if left_type == BaseType.INTEGER and right_type == BaseType.FLOAT:
            left = f"({left} as f64)"
        elif left_type == BaseType.FLOAT and right_type == BaseType.INTEGER:
            right = f"({right} as f64)"

        return f"({left} {op} {right})"

    def _get_expr_type(self, ctx) -> BaseType:
        """Get the resolved type of an expression from the symbol table or atlas."""
        # Special handling for function calls - look up return type from atlas
        if isinstance(ctx, ZincParser.FunctionCallExprContext):
            key = (self._current_function, ctx.getSourceInterval())
            mangled = self._specialization_map.get(key)
            if mangled and mangled in self.atlas.functions:
                return self.atlas.functions[mangled].return_type

        symbol = self.symbols.lookup_by_interval(
            ctx.getSourceInterval(), self._current_function
        )
        if symbol:
            return symbol.resolved_type
        return BaseType.UNKNOWN

    def _get_expr_symbol(self, ctx):
        """Get the resolved symbol for an expression-like context."""
        symbol = self.symbols.lookup_by_interval(
            ctx.getSourceInterval(), self._current_function
        )
        if symbol is not None:
            return symbol
        if isinstance(ctx, ZincParser.LambdaExprContext):
            return self.symbols.lookup_by_interval(
                ctx.lambdaExpression().getSourceInterval(), self._current_function
            )
        return None

    def _lookup_local_symbol(self, name: str):
        """Look up the latest resolved local/parameter symbol in the current function."""
        prefix = f"{self._current_function}."
        matches = [
            symbol
            for symbol in self.symbols.all_symbols()
            if symbol.id == name and symbol.unique_name.startswith(prefix)
        ]
        return matches[-1] if matches else None

    def _fallback_symbol_for_ctx(self, ctx):
        """Prefer the latest local binding when the interval symbol is a stale temporary."""
        if isinstance(ctx, ZincParser.PrimaryExprContext):
            primary = ctx.primaryExpression()
            if primary and primary.IDENTIFIER():
                return self._lookup_local_symbol(primary.IDENTIFIER().getText())
        return None

    def _get_dict_info(self, ctx) -> DictTypeInfo | None:
        """Get dict metadata for an expression."""
        symbol = self._get_expr_symbol(ctx)
        if symbol and symbol.dict_info:
            if (
                symbol.dict_info.key_type != BaseType.UNKNOWN
                or symbol.dict_info.value_type != BaseType.UNKNOWN
            ):
                return symbol.dict_info
        fallback = self._fallback_symbol_for_ctx(ctx)
        if fallback and fallback.dict_info:
            return fallback.dict_info
        if symbol and symbol.dict_info:
            return symbol.dict_info
        return None

    def _get_set_info(self, ctx) -> SetTypeInfo | None:
        """Get set metadata for an expression."""
        symbol = self._get_expr_symbol(ctx)
        if symbol and symbol.set_info:
            if symbol.set_info.element_type != BaseType.UNKNOWN:
                return symbol.set_info
        fallback = self._fallback_symbol_for_ctx(ctx)
        if fallback and fallback.set_info:
            return fallback.set_info
        if symbol and symbol.set_info:
            return symbol.set_info
        return None

    def _get_tuple_info(self, ctx) -> TupleTypeInfo | None:
        """Get tuple metadata for an expression."""
        symbol = self._get_expr_symbol(ctx)
        if symbol and symbol.tuple_info:
            if all(element != BaseType.UNKNOWN for element in symbol.tuple_info.element_types):
                return symbol.tuple_info
        fallback = self._fallback_symbol_for_ctx(ctx)
        if fallback and fallback.tuple_info:
            return fallback.tuple_info
        if symbol and symbol.tuple_info:
            return symbol.tuple_info
        return None

    def _coerce_owned(self, value: str, target_type: BaseType, value_ctx=None) -> str:
        """Convert a rendered value into the owned Rust type used inside collections."""
        if target_type == BaseType.STRING:
            if value.startswith('"'):
                return f"String::from({value})"
            return f"{value}.to_string()"
        if target_type == BaseType.FLOAT and value_ctx is not None:
            if self._get_expr_type(value_ctx) == BaseType.INTEGER:
                return f"({value} as f64)"
        return value

    def _borrow_lookup_key(self, value: str, key_type: BaseType) -> str:
        """Render a borrowed lookup key for map/set lookup-style methods."""
        if key_type == BaseType.STRING:
            if value.startswith('"'):
                return value
            return f"{value}.as_ref()"
        return f"&{value}"

    def _integer_literal_value(self, ctx) -> int | None:
        """Return an integer literal value for tuple indexes, if statically known."""
        if isinstance(ctx, ZincParser.PrimaryExprContext):
            primary = ctx.primaryExpression()
            if primary and primary.literal() and primary.literal().INTEGER():
                return int(primary.literal().getText(), 0)
        return None

    def _binding_names(self, ctx) -> list[str]:
        """Return identifier names from a binding/destructuring context."""
        return [token.getText() for token in ctx.getTokens(ZincParser.IDENTIFIER)]

    def _render_tuple_pattern(self, names: list[str]) -> str:
        """Render a Rust tuple pattern."""
        if len(names) == 1:
            return f"({names[0]},)"
        return f"({', '.join(names)})"

    def visitUnaryExpr(self, ctx: ZincParser.UnaryExprContext) -> str:
        """Visit unary expression."""
        op = ctx.getChild(0).getText()
        operand = self.visit(ctx.expression())
        return f"({op}{operand})"

    def visitRelationalExpr(self, ctx: ZincParser.RelationalExprContext) -> str:
        """Visit relational comparison."""
        left = self.visit(ctx.expression(0))
        op = ctx.getChild(1).getText()
        right = self.visit(ctx.expression(1))

        # Handle type promotion for comparisons: int < float -> cast int to f64
        left_type = self._get_expr_type(ctx.expression(0))
        right_type = self._get_expr_type(ctx.expression(1))

        if left_type == BaseType.INTEGER and right_type == BaseType.FLOAT:
            left = f"({left} as f64)"
        elif left_type == BaseType.FLOAT and right_type == BaseType.INTEGER:
            right = f"({right} as f64)"

        return f"({left} {op} {right})"

    def visitEqualityExpr(self, ctx: ZincParser.EqualityExprContext) -> str:
        """Visit equality comparison."""
        left = self.visit(ctx.expression(0))
        op = ctx.getChild(1).getText()
        right = self.visit(ctx.expression(1))

        # Handle type promotion for equality: int == float -> cast int to f64
        left_type = self._get_expr_type(ctx.expression(0))
        right_type = self._get_expr_type(ctx.expression(1))

        if left_type == BaseType.INTEGER and right_type == BaseType.FLOAT:
            left = f"({left} as f64)"
        elif left_type == BaseType.FLOAT and right_type == BaseType.INTEGER:
            right = f"({right} as f64)"

        return f"({left} {op} {right})"

    def visitLogicalAndExpr(self, ctx: ZincParser.LogicalAndExprContext) -> str:
        """Visit logical AND."""
        left = self.visit(ctx.expression(0))
        right = self.visit(ctx.expression(1))
        return f"({left} && {right})"

    def visitLogicalOrExpr(self, ctx: ZincParser.LogicalOrExprContext) -> str:
        """Visit logical OR."""
        left = self.visit(ctx.expression(0))
        right = self.visit(ctx.expression(1))
        return f"({left} || {right})"

    def visitArrayLiteral(self, ctx: ZincParser.ArrayLiteralContext) -> str:
        """Visit array literal."""
        elements = [self.visit(expr) for expr in ctx.expression()]
        return f"vec![{', '.join(elements)}]"

    def visitCollectionLiteral(self, ctx: ZincParser.CollectionLiteralContext) -> str:
        """Visit dict/set literal."""
        if ctx.dictEntry():
            info = self._expected_dict_info or self._get_dict_info(ctx) or DictTypeInfo()
            entries = []
            for entry_ctx in ctx.dictEntry():
                key_ctx = entry_ctx.expression(0)
                value_ctx = entry_ctx.expression(1)
                key = self._coerce_owned(self.visit(key_ctx), info.key_type, key_ctx)
                value = self._coerce_owned(self.visit(value_ctx), info.value_type, value_ctx)
                entries.append(f"({key}, {value})")
            return f"{info.rust_container()}::from([{', '.join(entries)}])"

        info = self._expected_set_info or self._get_set_info(ctx) or SetTypeInfo()
        elements = []
        for expr_ctx in ctx.expression():
            elem = self._coerce_owned(self.visit(expr_ctx), info.element_type, expr_ctx)
            elements.append(elem)
        return f"{info.rust_container()}::from([{', '.join(elements)}])"

    def visitIndexAccessExpr(self, ctx: ZincParser.IndexAccessExprContext) -> str:
        """Visit index access."""
        collection_type = self._get_expr_type(ctx.expression(0))
        collection = self.visit(ctx.expression(0))
        index = self.visit(ctx.expression(1))
        if collection_type == BaseType.DICT:
            info = self._get_dict_info(ctx.expression(0)) or DictTypeInfo()
            key = self._borrow_lookup_key(index, info.key_type)
            return f"{collection}.get({key}).unwrap().clone()"
        if collection_type == BaseType.TUPLE:
            tuple_index = self._integer_literal_value(ctx.expression(1))
            if tuple_index is not None:
                return f"{collection}.{tuple_index}"

        index_ctx = ctx.expression(1)
        # Cast non-literal integer indices to usize (Rust Vec indexing requires usize)
        index_type = self._get_expr_type(index_ctx)
        if index_type == BaseType.INTEGER and not self._is_integer_literal(index_ctx):
            index = f"({index} as usize)"
        return f"{collection}[{index}]"

    def _is_integer_literal(self, ctx) -> bool:
        """Return True if expression is a bare integer literal (e.g. 0, 1, 2)."""
        if isinstance(ctx, ZincParser.PrimaryExprContext):
            primary = ctx.primaryExpression()
            if primary and primary.literal():
                lit_text = primary.literal().getText()
                return bool(lit_text) and not lit_text.startswith('"') and '.' not in lit_text
        return False

    def visitRangeExpr(self, ctx: ZincParser.RangeExprContext) -> str:
        """Visit range expression."""
        start = self.visit(ctx.expression(0))
        end = self.visit(ctx.expression(1))
        if ctx.getChild(1).getText() == "..=":
            return f"{start}..={end}"
        return f"{start}..{end}"

    def visitMemberAccessExpr(self, ctx: ZincParser.MemberAccessExprContext) -> str:
        """Visit member access - could be field access or static method reference."""
        expr_symbol = self._get_expr_symbol(ctx)
        is_direct_call = (
            isinstance(ctx.parentCtx, ZincParser.FunctionCallExprContext)
            and ctx.parentCtx.expression() is ctx
        )
        if (
            expr_symbol
            and expr_symbol.resolved_type == BaseType.CALLABLE
            and expr_symbol.callable_info
            and not is_direct_call
        ):
            return self._render_callable_value(expr_symbol.callable_info)

        if self._current_module is not None:
            path = extract_identifier_path(ctx)
            if path:
                const_symbol = self.module_graph.resolve_const_path(self._current_module, path)
                if const_symbol:
                    const = self.atlas.consts.get(const_symbol.qualified_name)
                    if const:
                        return self._const_expr(const)
                    return self.module_graph.rust_base_name(const_symbol.qualified_name).upper()

                static_target = self.module_graph.resolve_static_method_target(self._current_module, path)
                if static_target:
                    struct_symbol, method_name = static_target
                    struct = self.atlas.structs.get(struct_symbol.qualified_name)
                    if struct:
                        return f"{self._struct_rust_name(struct)}::{method_name}"
                    return f"{self.module_graph.rust_base_name(struct_symbol.qualified_name)}::{method_name}"

                struct_symbol = self.module_graph.resolve_struct_path(self._current_module, path)
                if struct_symbol:
                    struct = self.atlas.structs.get(struct_symbol.qualified_name)
                    if struct:
                        return self._struct_rust_name(struct)
                    return self.module_graph.rust_base_name(struct_symbol.qualified_name)

        # Regular member access (field or instance method)
        obj = self.visit(ctx.expression())
        if isinstance(ctx.expression(), ZincParser.PrimaryExprContext):
            primary = ctx.expression().primaryExpression()
            if primary and primary.IDENTIFIER():
                receiver_name = primary.IDENTIFIER().getText()
                if self._boxed_struct_key(receiver_name) in self._boxed_struct_vars:
                    field_expr = f"{receiver_name}.borrow().{ctx.IDENTIFIER().getText()}"
                    expr_type = self._get_expr_type(ctx)
                    if expr_type in {
                        BaseType.STRING,
                        BaseType.ARRAY,
                        BaseType.DICT,
                        BaseType.SET,
                        BaseType.TUPLE,
                        BaseType.CALLABLE,
                        BaseType.STRUCT,
                    }:
                        return f"{field_expr}.clone()"
                    return field_expr
        return f"{obj}.{ctx.IDENTIFIER().getText()}"

    def visitFunctionCallExpr(self, ctx: ZincParser.FunctionCallExprContext) -> str:
        """Visit function call, handling static and instance method calls."""
        callee_ctx = ctx.expression()
        args = []
        arg_ctxs = []
        if ctx.argumentList():
            arg_ctxs = list(ctx.argumentList().expression())
            args = [self.visit(arg) for arg in arg_ctxs]

        # Get callee text first to check for static method
        callee = self.visit(callee_ctx)
        callee_symbol = self._get_expr_symbol(callee_ctx)

        if callee == "print":
            return self._render_print_call(args)

        if callee in {"dict", "sort_dict"}:
            info = self._expected_dict_info or self._get_dict_info(ctx) or DictTypeInfo(kind=callee)
            collection_type = info.rust_container()
            if info.key_type != BaseType.UNKNOWN and info.value_type != BaseType.UNKNOWN:
                key = type_to_rust(info.key_type)
                value = type_to_rust(info.value_type)
                return f"{collection_type}::<{key}, {value}>::new()"
            return f"{collection_type}::new()"

        if callee in {"set", "sort_set"}:
            info = self._expected_set_info or self._get_set_info(ctx) or SetTypeInfo(kind=callee)
            collection_type = info.rust_container()
            if info.element_type != BaseType.UNKNOWN:
                elem = type_to_rust(info.element_type)
                return f"{collection_type}::<{elem}>::new()"
            return f"{collection_type}::new()"

        # Static method call (StructName::method)
        if "::" in callee:
            struct_name, method_name = callee.rsplit("::", 1)
            struct = next((s for s in self.atlas.structs.values() if self._struct_rust_name(s) == struct_name), None)
            if struct:
                args = self._process_method_args(struct, method_name, args, arg_ctxs)
            return f"{callee}({', '.join(args)})"

        if (
            callee_symbol
            and callee_symbol.resolved_type == BaseType.CALLABLE
            and callee_symbol.callable_info
            and not isinstance(callee_ctx, ZincParser.MemberAccessExprContext)
        ):
            is_bare_top_level_function = False
            if isinstance(callee_ctx, ZincParser.PrimaryExprContext):
                primary = callee_ctx.primaryExpression()
                if primary and primary.IDENTIFIER():
                    name = primary.IDENTIFIER().getText()
                    is_bare_top_level_function = (
                        name not in self._declared_vars
                        and self._current_module is not None
                        and self.module_graph.resolve_function_path(self._current_module, [name]) is not None
                    )
            if not is_bare_top_level_function:
                args = self._process_callable_args(callee_symbol.callable_info, args, arg_ctxs)
                callable_expr = callee
                if isinstance(callee_ctx, ZincParser.MemberAccessExprContext):
                    callable_expr = self._render_callable_value(callee_symbol.callable_info)
                return f"{callable_expr}.call({', '.join(args)})"

        if self._current_module is not None:
            path = extract_identifier_path(callee_ctx)
            if path:
                resolved_function = self.module_graph.resolve_function_path(self._current_module, path)
                if resolved_function:
                    key = (self._current_function, ctx.getSourceInterval())
                    mangled = self._specialization_map.get(key) or self.module_graph.rust_base_name(
                        resolved_function.qualified_name
                    )
                    args = self._process_function_args(mangled, args, arg_ctxs)
                    call = f"{mangled}({', '.join(args)})"
                    if self.atlas.functions.get(mangled) and self.atlas.functions[mangled].is_async:
                        return f"{call}.await"
                    return call

        # Instance method call (obj.method) - already visited, callee is "obj.method"
        if isinstance(callee_ctx, ZincParser.MemberAccessExprContext):
            # Check if this is an instance method on a struct variable
            target_ctx = callee_ctx.expression()
            method_name = callee_ctx.IDENTIFIER().getText()
            receiver_type = self._get_expr_type(target_ctx)
            if receiver_type == BaseType.DICT:
                target = self.visit(target_ctx)
                info = self._get_dict_info(target_ctx) or DictTypeInfo()
                if method_name == "len":
                    return f"({target}.len() as i64)"
                if method_name == "is_empty":
                    return f"{target}.is_empty()"
                if method_name == "clear":
                    return f"{target}.clear()"
                if method_name == "keys":
                    return f"{target}.keys().cloned().collect::<Vec<_>>()"
                if method_name == "values":
                    return f"{target}.values().cloned().collect::<Vec<_>>()"
                if method_name == "items":
                    return f"{target}.iter().map(|(k, v)| (k.clone(), v.clone())).collect::<Vec<_>>()"
                if method_name == "insert" and len(args) == 2:
                    key = self._coerce_owned(args[0], info.key_type, arg_ctxs[0] if arg_ctxs else None)
                    value = self._coerce_owned(args[1], info.value_type, arg_ctxs[1] if arg_ctxs else None)
                    return f"{target}.insert({key}, {value})"
                if method_name in {"get", "contains_key", "remove"} and len(args) == 1:
                    key = self._borrow_lookup_key(args[0], info.key_type)
                    if method_name == "get":
                        return f"{target}.get({key}).unwrap().clone()"
                    return f"{target}.{method_name}({key})"

            if receiver_type == BaseType.SET:
                target = self.visit(target_ctx)
                info = self._get_set_info(target_ctx) or SetTypeInfo()
                if method_name == "len":
                    return f"({target}.len() as i64)"
                if method_name == "is_empty":
                    return f"{target}.is_empty()"
                if method_name == "clear":
                    return f"{target}.clear()"
                if method_name in {"push", "insert"} and len(args) == 1:
                    elem = self._coerce_owned(args[0], info.element_type, arg_ctxs[0] if arg_ctxs else None)
                    return f"{target}.insert({elem})"
                if method_name in {"contains", "remove"} and len(args) == 1:
                    elem = self._borrow_lookup_key(args[0], info.element_type)
                    return f"{target}.{method_name}({elem})"

            if receiver_type == BaseType.ARRAY and method_name == "push" and len(args) == 1:
                receiver_symbol = self._get_expr_symbol(target_ctx)
                if isinstance(target_ctx, ZincParser.PrimaryExprContext):
                    primary = target_ctx.primaryExpression()
                    if primary and primary.IDENTIFIER():
                        receiver_symbol = self._lookup_local_symbol(primary.IDENTIFIER().getText()) or receiver_symbol
                arg_ctx = arg_ctxs[0] if arg_ctxs else None
                arg_symbol = self._get_expr_symbol(arg_ctx) if arg_ctx is not None else None
                if (
                    receiver_symbol
                    and receiver_symbol.element_type == BaseType.CALLABLE
                    and receiver_symbol.callable_info
                    and arg_symbol
                    and arg_symbol.callable_info
                ):
                    args[0] = self._render_callable_value_for_signature(
                        arg_symbol.callable_info,
                        receiver_symbol.callable_info,
                    )

            if isinstance(target_ctx, ZincParser.PrimaryExprContext):
                primary = target_ctx.primaryExpression()
                if primary and primary.IDENTIFIER():
                    target_var = primary.IDENTIFIER().getText()
                    key = f"{self._current_function}:{target_var}"
                    if key in self._struct_instance_vars:
                        struct_name = self._struct_instance_vars[key]
                        struct = self.atlas.structs.get(struct_name)
                        if struct:
                            args = self._process_method_args(struct, method_name, args, arg_ctxs)
                            method = next((m for m in struct.methods if m.name == method_name), None)
                            if self._boxed_struct_key(target_var) in self._boxed_struct_vars and method:
                                borrow = "borrow_mut" if method.self_mutability == "&mut self" else "borrow"
                                result = f"{target_var}.{borrow}().{method_name}({', '.join(args)})"
                                if method_name == "len":
                                    return f"({result} as i64)"
                                return result
            result = f"{callee}({', '.join(args)})"
            # len() returns usize in Rust but Zinc treats all integers as i64
            if method_name == "len":
                return f"({result} as i64)"
            return result

        # Look up mangled name from specialization map (scoped by current function)
        key = (self._current_function, ctx.getSourceInterval())
        mangled = self._specialization_map.get(key)
        if mangled:
            # Process arguments for string literal conversion
            args = self._process_function_args(mangled, args, arg_ctxs)
            call = f"{mangled}({', '.join(args)})"
            if self.atlas.functions.get(mangled) and self.atlas.functions[mangled].is_async:
                return f"{call}.await"
            return call

        return f"{callee}({', '.join(args)})"

    def _process_function_args(
        self,
        mangled_name: str,
        args: list[str],
        arg_ctxs: list | None = None,
    ) -> list[str]:
        """Process function arguments: String conversion, array references."""
        func = self.atlas.functions.get(mangled_name)
        if not func:
            return args

        processed = []
        for i, arg in enumerate(args):
            if i < len(func.arg_types):
                param_type = func.arg_types[i]

                # Convert string literal to String::from() for String parameters
                if param_type == BaseType.STRING and arg.startswith('"'):
                    processed.append(f"String::from({arg})")
                elif param_type == BaseType.CHANNEL and i in func.arg_channel_infos:
                    arg_ctx = arg_ctxs[i] if arg_ctxs and i < len(arg_ctxs) else None
                    if isinstance(arg_ctx, ZincParser.PrimaryExprContext):
                        primary = arg_ctx.primaryExpression()
                        if primary and primary.IDENTIFIER():
                            processed.append(self._channel_sender_expr(primary.IDENTIFIER().getText(), clone=True))
                            continue
                    processed.append(f"{arg}.clone()")
                # Pass arrays by reference
                elif param_type == BaseType.ARRAY and i in func.arg_array_infos:
                    arr_info = func.arg_array_infos[i]
                    if arr_info.is_mutated:
                        processed.append(f"&mut {arg}")
                    else:
                        processed.append(f"&{arg}")
                elif param_type == BaseType.DICT and i in func.arg_dict_infos:
                    dict_info = func.arg_dict_infos[i]
                    if dict_info.is_mutated:
                        processed.append(f"&mut {arg}")
                    else:
                        processed.append(f"&{arg}")
                elif param_type == BaseType.SET and i in func.arg_set_infos:
                    set_info = func.arg_set_infos[i]
                    if set_info.is_mutated:
                        processed.append(f"&mut {arg}")
                    else:
                        processed.append(f"&{arg}")
                elif param_type == BaseType.CALLABLE and i in func.arg_callable_infos:
                    arg_ctx = arg_ctxs[i] if arg_ctxs and i < len(arg_ctxs) else None
                    arg_symbol = self._get_expr_symbol(arg_ctx) if arg_ctx is not None else None
                    is_local_callable = (
                        isinstance(arg_ctx, ZincParser.PrimaryExprContext)
                        and arg_ctx.primaryExpression()
                        and arg_ctx.primaryExpression().IDENTIFIER()
                        and arg_ctx.primaryExpression().IDENTIFIER().getText() in self._declared_vars
                    )
                    if arg_symbol and arg_symbol.callable_info and not is_local_callable:
                        processed.append(
                            self._render_callable_value_for_signature(
                                arg_symbol.callable_info,
                                func.arg_callable_infos[i],
                            )
                        )
                    else:
                        processed.append(f"{arg}.clone()")
                else:
                    processed.append(arg)
            else:
                processed.append(arg)

        return processed

    def _process_method_args(
        self,
        struct: StructInstance,
        method_name: str,
        args: list[str],
        arg_ctxs: list | None = None,
    ) -> list[str]:
        """Process method arguments: String conversion and integer narrowing."""
        method = next((m for m in struct.methods if m.name == method_name), None)
        if not method:
            return args

        processed = []
        for i, arg in enumerate(args):
            if i < len(method.parameters):
                _, type_ann, resolved = method.parameters[i]
                param_type = type_ann or resolved

                # Convert string literal to String::from() for String parameters
                if param_type and param_type.lower() == "string" and arg.startswith('"'):
                    processed.append(f"String::from({arg})")
                # Apply integer narrowing for literals
                elif param_type and param_type in ("i32", "i64"):
                    arg_ctx = arg_ctxs[i] if arg_ctxs and i < len(arg_ctxs) else None
                    narrowed = self._apply_literal_narrowing(arg, param_type, arg_ctx)
                    processed.append(narrowed)
                else:
                    processed.append(arg)
            else:
                processed.append(arg)

        return processed

    def _apply_literal_narrowing(
        self, arg: str, target_type: str, arg_ctx=None
    ) -> str:
        """Apply safe integer narrowing when argument is a literal expression.

        Only narrows when the argument is:
        1. A direct numeric literal (e.g., 5, 100)
        2. An expression containing only literals and calls to functions returning literals
        """
        if target_type not in ("i32", "i64"):
            return arg

        # Check if the expression contains only compile-time known values
        if self._is_compile_time_literal_expr(arg_ctx):
            # If target is i32 and we have an i64-inferred expression, cast it
            if target_type == "i32":
                # Wrap the expression with an explicit cast
                return f"({arg}) as i32"

        return arg

    def _is_compile_time_literal_expr(self, ctx) -> bool:
        """Check if expression contains only compile-time known literal values.

        Returns True for:
        - Numeric literals
        - Expressions of literals (e.g., 100 + 5)
        - Calls to static methods that return literal values
        - Variables that were assigned compile-time literal values
        """
        if ctx is None:
            return False

        # Direct literal
        if isinstance(ctx, ZincParser.PrimaryExprContext):
            primary = ctx.primaryExpression()
            if primary:
                if primary.literal():
                    lit_text = primary.literal().getText()
                    # Check if it's a numeric literal (not a string)
                    if lit_text and not lit_text.startswith('"'):
                        return True
                # Variable reference - check if it's a known literal variable
                if primary.IDENTIFIER():
                    var_name = primary.IDENTIFIER().getText()
                    return var_name in self._literal_vars
            return False

        # Binary expressions (additive, multiplicative)
        if isinstance(ctx, (ZincParser.AdditiveExprContext, ZincParser.MultiplicativeExprContext)):
            left = ctx.expression(0)
            right = ctx.expression(1)
            return self._is_compile_time_literal_expr(left) and self._is_compile_time_literal_expr(right)

        # Parenthesized expression
        if isinstance(ctx, ZincParser.ParenExprContext):
            return self._is_compile_time_literal_expr(ctx.expression())

        # Function call - check if it's a static method returning a literal
        if isinstance(ctx, ZincParser.FunctionCallExprContext):
            callee_ctx = ctx.expression()
            if isinstance(callee_ctx, ZincParser.MemberAccessExprContext):
                target_text = callee_ctx.expression().getText()
                method_name = callee_ctx.IDENTIFIER().getText()
                # Check if this is a static method call on a struct
                struct = next((s for s in self.atlas.structs.values() if s.name == target_text), None)
                if struct:
                    method = next((m for m in struct.methods if m.name == method_name), None)
                    if method and method.is_static and method.body_ctx:
                        # Check if method body is just "return <literal>"
                        return self._method_returns_literal(method.body_ctx)
            return False

        return False

    def _method_returns_literal(self, block_ctx) -> bool:
        """Check if a method body is just 'return <literal>'."""
        if not block_ctx:
            return False
        stmts = block_ctx.statement()
        if len(stmts) != 1:
            return False
        stmt = stmts[0]
        if not stmt.returnStatement():
            return False
        ret_stmt = stmt.returnStatement()
        if not ret_stmt.expression():
            return False
        expr = ret_stmt.expression()
        # Check if expression is a literal
        if isinstance(expr, ZincParser.PrimaryExprContext):
            primary = expr.primaryExpression()
            if primary and primary.literal():
                lit_text = primary.literal().getText()
                return lit_text and not lit_text.startswith('"')
        return False

    def _render_print_call(self, args: list[str]) -> str:
        """Render a print() call as println!()."""
        if not args:
            return 'println!()'
        arg = args[0]
        if arg.startswith('format!('):
            inner = arg[8:-1]
            return f"println!({inner})"
        if arg.startswith('"'):
            inner = arg[1:-1]
            interpolations = re.findall(r"\{([^}]+)\}", inner)
            if interpolations:
                format_str = re.sub(r"\{[^}]+\}", "{}", inner)
                expr_args = ", ".join(self._rewrite_interpolation_expr(expr) for expr in interpolations)
                return f'println!("{format_str}", {expr_args})'
            return f'println!("{inner}")'
        return f"println!(\"{{}}\", {arg})"


    def visitChannelReceiveExpr(self, ctx: ZincParser.ChannelReceiveExprContext) -> str:
        """Visit channel receive expression."""
        chan_expr = ctx.expression()
        if isinstance(chan_expr, ZincParser.PrimaryExprContext):
            primary = chan_expr.primaryExpression()
            if primary and primary.IDENTIFIER():
                chan_name = primary.IDENTIFIER().getText()
                return f"{self._channel_receiver_expr(chan_name)}.recv().await.unwrap()"
        receiver = self.visit(chan_expr)
        return f"{receiver}.recv().await.unwrap()"

    def visitStructInstantiation(self, ctx: ZincParser.StructInstantiationContext) -> str:
        """Visit struct instantiation."""
        if self._current_module is None:
            name = ctx.qualifiedName().getText()
            struct = None
        else:
            struct_symbol = self.module_graph.resolve_struct_path(
                self._current_module, struct_path_from_ctx(ctx)
            )
            if (
                struct_symbol is not None
                and self._current_struct is not None
                and self._current_constructor_owner is not None
                and struct_symbol.qualified_name == self._current_constructor_owner
            ):
                struct = self.atlas.structs.get(self._current_struct)
                name = self._struct_rust_name(struct) if struct else ctx.qualifiedName().getText()
            else:
                struct = self.atlas.structs.get(struct_symbol.qualified_name) if struct_symbol else None
                name = self._struct_rust_name(struct) if struct else ctx.qualifiedName().getText()

        # Get provided field values
        provided_fields: dict[str, str] = {}
        for field_ctx in ctx.fieldInit():
            field_name = field_ctx.IDENTIFIER().getText()
            field_value = self.visit(field_ctx.expression())
            provided_fields[field_name] = field_value

        # Look up struct definition to get all fields with defaults
        if struct:
            fields = []
            for f in struct.fields:
                if f.name in provided_fields:
                    value = provided_fields[f.name]
                    # Convert string literals to String::from() for String fields
                    if f.rust_type() == "String" and value.startswith('"'):
                        value = f"String::from({value})"
                    fields.append(f"{f.name}: {value}")
                else:
                    # Use default value
                    fields.append(f"{f.name}: {f.rust_default()}")
            fields_str = ", ".join(fields)
            return f"{name} {{ {fields_str} }}"
        else:
            # Fallback - just use provided fields
            fields = [f"{k}: {v}" for k, v in provided_fields.items()]
            fields_str = ", ".join(fields)
            return f"{name} {{ {fields_str} }}"

    # --- Statement Visitors (return Rust statement strings) ---

    def visitVariableAssignment(self, ctx: ZincParser.VariableAssignmentContext) -> str:
        """Visit variable assignment with shadowing support."""
        target = ctx.assignmentTarget().getText()
        target_ctx = ctx.assignmentTarget()

        # Check if this is a chan() call - generate tuple destructuring
        expr = ctx.expression()
        if isinstance(expr, ZincParser.FunctionCallExprContext):
            callee = expr.expression()
            if isinstance(callee, ZincParser.PrimaryExprContext):
                primary = callee.primaryExpression()
                if primary and primary.IDENTIFIER() and primary.IDENTIFIER().getText() == "chan":
                    var_name = target
                    capacity = None
                    if expr.argumentList() and expr.argumentList().expression():
                        capacity = self.visit(expr.argumentList().expression(0))
                    # Look up channel info to get element type
                    if var_name in self._channel_infos:
                        chan_info = self._channel_infos[var_name]
                        elem_type = type_to_rust(chan_info.element_type)
                        self._declared_vars.add(var_name)
                        if chan_info.is_bounded and capacity is not None:
                            return f"let ({var_name}_tx, mut {var_name}_rx) = tokio::sync::mpsc::channel::<{elem_type}>({capacity});"
                        return f"let ({var_name}_tx, mut {var_name}_rx) = tokio::sync::mpsc::unbounded_channel::<{elem_type}>();"
                    else:
                        # Fallback - unknown element type
                        self._declared_vars.add(var_name)
                        if capacity is not None:
                            return f"let ({var_name}_tx, mut {var_name}_rx) = tokio::sync::mpsc::channel({capacity});"
                        return f"let ({var_name}_tx, mut {var_name}_rx) = tokio::sync::mpsc::unbounded_channel();"

        target_symbol = None
        if target_ctx.IDENTIFIER():
            target_symbol = self.symbols.lookup_by_interval(
                target_ctx.IDENTIFIER().getSourceInterval(), self._current_function
            )

        previous_dict_info = self._expected_dict_info
        previous_set_info = self._expected_set_info
        previous_tuple_info = self._expected_tuple_info
        if target_symbol and target_symbol.dict_info:
            self._expected_dict_info = target_symbol.dict_info
        if target_symbol and target_symbol.set_info:
            self._expected_set_info = target_symbol.set_info
        if target_symbol and target_symbol.tuple_info:
            self._expected_tuple_info = target_symbol.tuple_info
        try:
            value = self.visit(expr)
        finally:
            self._expected_dict_info = previous_dict_info
            self._expected_set_info = previous_set_info
            self._expected_tuple_info = previous_tuple_info

        expr_symbol = self._get_expr_symbol(expr)
        is_local_callable = (
            isinstance(expr, ZincParser.PrimaryExprContext)
            and expr.primaryExpression()
            and expr.primaryExpression().IDENTIFIER()
            and expr.primaryExpression().IDENTIFIER().getText() in self._declared_vars
        )
        if (
            target_symbol
            and target_symbol.resolved_type == BaseType.CALLABLE
            and target_symbol.callable_info
            and expr_symbol
            and expr_symbol.callable_info
            and len(expr_symbol.callable_info.targets) == 1
            and not is_local_callable
        ):
            value = self._render_callable_value_for_signature(
                expr_symbol.callable_info,
                target_symbol.callable_info,
            )

        if target_ctx.IDENTIFIER():
            boxed_key = self._boxed_struct_key(target)
            if boxed_key in self._boxed_struct_vars:
                if isinstance(expr, ZincParser.PrimaryExprContext):
                    primary = expr.primaryExpression()
                    if primary and primary.IDENTIFIER():
                        source_name = primary.IDENTIFIER().getText()
                        if self._boxed_struct_key(source_name) in self._boxed_struct_vars:
                            value = f"{value}.clone()"
                        else:
                            value = f"Rc::new(RefCell::new({value}))"
                    else:
                        value = f"Rc::new(RefCell::new({value}))"
                else:
                    value = f"Rc::new(RefCell::new({value}))"

        if target_ctx.tupleAssignmentTarget():
            names = self._binding_names(target_ctx.tupleAssignmentTarget())
            target_symbols = [
                self.symbols.lookup_by_interval(token.getSourceInterval(), self._current_function)
                for token in target_ctx.tupleAssignmentTarget().getTokens(ZincParser.IDENTIFIER)
            ]
            needs_declaration = any(
                symbol is None or symbol.is_shadow or symbol.id not in self._declared_vars
                for symbol in target_symbols
            )
            pattern_names = []
            for name, symbol in zip(names, target_symbols, strict=False):
                if needs_declaration and symbol and symbol.is_mutated:
                    pattern_names.append(f"mut {name}")
                else:
                    pattern_names.append(name)
                if needs_declaration:
                    self._declared_vars.add(name)
            pattern = self._render_tuple_pattern(pattern_names)
            if needs_declaration:
                return f"let {pattern} = {value};"
            return f"{pattern} = {value};"

        if target_ctx.indexAccess():
            index_access = target_ctx.indexAccess()
            collection_type = self._get_expr_type(index_access.expression(0))
            if collection_type == BaseType.DICT:
                info = self._get_dict_info(index_access.expression(0)) or DictTypeInfo()
                collection = self.visit(index_access.expression(0))
                key_ctx = index_access.expression(1)
                key = self._coerce_owned(self.visit(key_ctx), info.key_type, key_ctx)
                coerced_value = self._coerce_owned(value, info.value_type, expr)
                return f"{collection}.insert({key}, {coerced_value});"

        if target_ctx.IDENTIFIER():
            var_name = target
            symbol = target_symbol

            if symbol is None:
                # Fallback - shouldn't happen
                return f"let {var_name} = {value};"

            if symbol.is_shadow or var_name not in self._declared_vars:
                # First declaration OR shadow (type change) -> use let
                self._declared_vars.add(var_name)
                # Check if this is a struct var that needs mut
                needs_mut = symbol.is_mutated or var_name in self._mut_struct_vars
                if needs_mut:
                    return f"let mut {var_name} = {value};"
                return f"let {var_name} = {value};"
            else:
                # Same-type reassignment -> bare assignment
                return f"{var_name} = {value};"

        return f"{target} = {value};"

    def visitIfStatement(self, ctx: ZincParser.IfStatementContext) -> str:
        """Visit if statement."""
        lines = []
        expressions = ctx.expression()
        blocks = ctx.block()

        for i, expr in enumerate(expressions):
            cond = self.visit(expr)
            body_stmts = self._generate_block(blocks[i])
            keyword = "if" if i == 0 else "} else if"
            lines.append(f"{keyword} {cond} {{")
            for stmt in body_stmts:
                # Handle multi-line statements (like nested if/while)
                for line in stmt.split("\n"):
                    lines.append(f"    {line}")

        if len(blocks) > len(expressions):
            lines.append("} else {")
            body_stmts = self._generate_block(blocks[-1])
            for stmt in body_stmts:
                for line in stmt.split("\n"):
                    lines.append(f"    {line}")

        lines.append("}")
        return "\n".join(lines)

    def _render_for_iterable(self, expr_ctx) -> str:
        """Render an iterable expression for a for loop without consuming named collections."""
        expr_type = self._get_expr_type(expr_ctx)

        if expr_type == BaseType.DICT:
            target = self.visit(expr_ctx)
            return f"{target}.iter().map(|(k, v)| (k.clone(), v.clone()))"

        if isinstance(expr_ctx, ZincParser.FunctionCallExprContext):
            callee = expr_ctx.expression()
            if isinstance(callee, ZincParser.MemberAccessExprContext):
                receiver_type = self._get_expr_type(callee.expression())
                method_name = callee.IDENTIFIER().getText()
                if receiver_type == BaseType.DICT and method_name in {"keys", "values", "items"}:
                    target = self.visit(callee.expression())
                    if method_name == "keys":
                        return f"{target}.keys().cloned()"
                    if method_name == "values":
                        return f"{target}.values().cloned()"
                    return f"{target}.iter().map(|(k, v)| (k.clone(), v.clone()))"

        rendered = self.visit(expr_ctx)
        if expr_type in {BaseType.ARRAY, BaseType.SET}:
            return f"{rendered}.iter().cloned()"
        return rendered

    def visitForStatement(self, ctx: ZincParser.ForStatementContext) -> str:
        """Visit for loop."""
        binding = ctx.forBinding()
        binding_ctx = binding.tupleAssignmentTarget() or binding
        names = self._binding_names(binding_ctx)
        var_name = names[0] if len(names) == 1 else self._render_tuple_pattern(names)
        iterable = self._render_for_iterable(ctx.expression())
        body_stmts = self._generate_block(ctx.block())

        lines = [f"for {var_name} in {iterable} {{"]
        for stmt in body_stmts:
            # Handle multi-line statements (like nested if/while)
            for line in stmt.split("\n"):
                lines.append(f"    {line}")
        lines.append("}")
        return "\n".join(lines)

    def visitWhileStatement(self, ctx: ZincParser.WhileStatementContext) -> str:
        """Visit while loop."""
        cond = self.visit(ctx.expression())
        body_stmts = self._generate_block(ctx.block())

        lines = [f"while {cond} {{"]
        for stmt in body_stmts:
            # Handle multi-line statements (like nested if/while)
            for line in stmt.split("\n"):
                lines.append(f"    {line}")
        lines.append("}")
        return "\n".join(lines)

    def visitLoopStatement(self, ctx: ZincParser.LoopStatementContext) -> str:
        """Visit infinite loop."""
        body_stmts = self._generate_block(ctx.block())

        lines = ["loop {"]
        for stmt in body_stmts:
            # Handle multi-line statements (like nested if/while)
            for line in stmt.split("\n"):
                lines.append(f"    {line}")
        lines.append("}")
        return "\n".join(lines)

    def _next_select_id(self) -> int:
        """Return a unique id for generated select helper names."""
        select_id = self._select_counter
        self._select_counter += 1
        return select_id

    def _render_select_case_body(self, block_ctx, binding_name: str | None = None, binding_source: str | None = None) -> list[str]:
        """Render a select case body, keeping header bindings local to the case."""
        prelude: list[str] = []
        local_names: set[str] | None = None
        if binding_name and binding_source:
            prelude.append(f"let {binding_name} = {binding_source};")
            local_names = {binding_name}
        return self._render_scoped_block(block_ctx, prelude=prelude, local_names=local_names)

    def _render_select_without_default(self, case_ctxs: list, select_id: int) -> str:
        """Lower a blocking select to tokio::select!."""
        lines = ["tokio::select! {"]
        for branch_index, case_ctx in enumerate(case_ctxs):
            if isinstance(case_ctx, ZincParser.SelectReceiveCaseContext):
                binding_name = case_ctx.IDENTIFIER(0).getText()
                channel_name = case_ctx.IDENTIFIER(1).getText()
                recv_name = f"__zinc_select_value_{select_id}_{branch_index}"
                receiver = self._channel_receiver_expr(channel_name)
                body = self._render_select_case_body(case_ctx.block(), binding_name, recv_name)
                lines.append(f"    {recv_name} = async {{ {receiver}.recv().await.unwrap() }} => {{")
                self._append_block_lines(lines, body, 2)
                lines.append("    },")
                continue

            channel_name = case_ctx.IDENTIFIER().getText()
            sender = self._channel_sender_expr(channel_name)
            value = self._render_channel_value(channel_name, case_ctx.expression())
            chan_info = self._channel_infos.get(channel_name)
            body = self._render_select_case_body(case_ctx.block())
            if chan_info and chan_info.is_bounded:
                result_name = f"__zinc_select_result_{select_id}_{branch_index}"
                lines.append(f"    {result_name} = {sender}.send({value}) => {{")
                lines.append(f"        {result_name}.unwrap();")
            else:
                lines.append(f"    _ = async {{ {sender}.send({value}).unwrap(); }} => {{")
            self._append_block_lines(lines, body, 2)
            lines.append("    },")
        lines.append("}")
        return "\n".join(lines)

    def _render_select_with_default(self, case_ctxs: list, default_case, select_id: int) -> str:
        """Lower a non-blocking select with default using explicit probe order."""
        default_body = self._render_select_case_body(default_case.block())
        if not case_ctxs:
            lines = ["{"]
            self._append_block_lines(lines, default_body, 1)
            lines.append("}")
            return "\n".join(lines)

        label = f"'__zinc_select_{select_id}"
        static_name = f"__ZINC_SELECT_STATE_{select_id}"
        start_name = f"__zinc_select_start_{select_id}"
        offset_name = f"__zinc_select_offset_{select_id}"
        case_count = len(case_ctxs)

        lines = [
            f"static {static_name}: std::sync::atomic::AtomicUsize = std::sync::atomic::AtomicUsize::new(0);",
            f"let {start_name} = {static_name}.fetch_add(1, std::sync::atomic::Ordering::Relaxed) % {case_count};",
            f"{label}: {{",
            f"    for {offset_name} in 0..{case_count} {{",
            f"        match ({start_name} + {offset_name}) % {case_count} {{",
        ]

        for branch_index, case_ctx in enumerate(case_ctxs):
            lines.append(f"            {branch_index} => {{")
            if isinstance(case_ctx, ZincParser.SelectReceiveCaseContext):
                binding_name = case_ctx.IDENTIFIER(0).getText()
                channel_name = case_ctx.IDENTIFIER(1).getText()
                value_name = f"__zinc_select_value_{select_id}_{branch_index}"
                receiver = self._channel_receiver_expr(channel_name)
                body = self._render_select_case_body(case_ctx.block(), binding_name, value_name)
                lines.append(f"                match {receiver}.try_recv() {{")
                lines.append(f"                    Ok({value_name}) => {{")
                self._append_block_lines(lines, body, 6)
                lines.append(f"                        break {label};")
                lines.append("                    },")
                lines.append("                    Err(tokio::sync::mpsc::error::TryRecvError::Empty) => {},")
                lines.append('                    Err(tokio::sync::mpsc::error::TryRecvError::Disconnected) => panic!("select receive on closed channel"),')
                lines.append("                }")
            else:
                channel_name = case_ctx.IDENTIFIER().getText()
                sender = self._channel_sender_expr(channel_name)
                value = self._render_channel_value(channel_name, case_ctx.expression())
                chan_info = self._channel_infos.get(channel_name)
                body = self._render_select_case_body(case_ctx.block())
                if chan_info and chan_info.is_bounded:
                    lines.append(f"                match {sender}.try_send({value}) {{")
                    lines.append("                    Ok(()) => {")
                    self._append_block_lines(lines, body, 6)
                    lines.append(f"                        break {label};")
                    lines.append("                    },")
                    lines.append("                    Err(tokio::sync::mpsc::error::TrySendError::Full(_)) => {},")
                    lines.append('                    Err(tokio::sync::mpsc::error::TrySendError::Closed(_)) => panic!("select send on closed channel"),')
                    lines.append("                }")
                else:
                    lines.append(f"                match {sender}.send({value}) {{")
                    lines.append("                    Ok(()) => {")
                    self._append_block_lines(lines, body, 6)
                    lines.append(f"                        break {label};")
                    lines.append("                    },")
                    lines.append('                    Err(_) => panic!("select send on closed channel"),')
                    lines.append("                }")
            lines.append("            }")

        lines.extend([
            "            _ => unreachable!(),",
            "        }",
            "    }",
        ])
        self._append_block_lines(lines, default_body, 1)
        lines.append("}")
        return "\n".join(lines)

    def visitSelectStatement(self, ctx: ZincParser.SelectStatementContext) -> str:
        """Visit a select statement."""
        select_id = self._next_select_id()
        cases = list(ctx.selectCase())
        default_case = next(
            (case_ctx for case_ctx in cases if isinstance(case_ctx, ZincParser.SelectDefaultCaseContext)),
            None,
        )
        non_default_cases = [
            case_ctx
            for case_ctx in cases
            if not isinstance(case_ctx, ZincParser.SelectDefaultCaseContext)
        ]
        if default_case is not None:
            return self._render_select_with_default(non_default_cases, default_case, select_id)
        return self._render_select_without_default(non_default_cases, select_id)

    def visitReturnStatement(self, ctx: ZincParser.ReturnStatementContext) -> str:
        """Visit return statement."""
        if ctx.expression():
            func = self.atlas.functions.get(self._current_function)
            previous_dict_info = self._expected_dict_info
            previous_set_info = self._expected_set_info
            previous_tuple_info = self._expected_tuple_info
            if func and func.return_dict_info:
                self._expected_dict_info = func.return_dict_info
            if func and func.return_set_info:
                self._expected_set_info = func.return_set_info
            if func and func.return_tuple_info:
                self._expected_tuple_info = func.return_tuple_info
            try:
                value = self.visit(ctx.expression())
            finally:
                self._expected_dict_info = previous_dict_info
                self._expected_set_info = previous_set_info
                self._expected_tuple_info = previous_tuple_info
            if func and func.return_type == BaseType.CALLABLE and func.return_callable_info:
                expr_symbol = self._get_expr_symbol(ctx.expression())
                is_local_callable = (
                    isinstance(ctx.expression(), ZincParser.PrimaryExprContext)
                    and ctx.expression().primaryExpression()
                    and ctx.expression().primaryExpression().IDENTIFIER()
                    and ctx.expression().primaryExpression().IDENTIFIER().getText() in self._declared_vars
                )
                if expr_symbol and expr_symbol.callable_info and not is_local_callable:
                    value = self._render_callable_value_for_signature(
                        expr_symbol.callable_info,
                        func.return_callable_info,
                    )
            # Cast integer return values to f64 when function return type is float
            if func and func.return_type == BaseType.FLOAT:
                expr_type = self._get_expr_type(ctx.expression())
                if expr_type == BaseType.INTEGER:
                    value = f"({value} as f64)"
            return self._render_return(f"return {value};")
        return self._render_return("return;")

    def _render_return(self, return_stmt: str) -> str:
        """Render a return statement, awaiting local spawned tasks first."""
        if not self._spawn_handles_var:
            return return_stmt
        return "\n".join([
            self._render_spawn_handle_awaits(self._spawn_handles_var),
            return_stmt,
        ])

    def visitBreakStatement(self, ctx: ZincParser.BreakStatementContext) -> str:
        """Visit break statement."""
        return "break;"

    def visitContinueStatement(self, ctx: ZincParser.ContinueStatementContext) -> str:
        """Visit continue statement."""
        return "continue;"

    def visitSpawnStatement(self, ctx: ZincParser.SpawnStatementContext) -> str:
        """Visit spawn statement, using mangled name for spawned function."""
        self._uses_async = True
        # Grammar: spawn expression '(' argumentList? ')'
        # The expression is the function name, and args are in argumentList
        func_name = self.visit(ctx.expression())
        args = []
        setup = []
        if ctx.argumentList():
            for i, arg in enumerate(ctx.argumentList().expression()):
                arg_code = self.visit(arg)
                if isinstance(arg, ZincParser.PrimaryExprContext):
                    primary = arg.primaryExpression()
                    if primary and primary.IDENTIFIER():
                        var_name = primary.IDENTIFIER().getText()
                        if var_name in self._channel_infos:
                            arg_code = f"__zinc_spawn_arg_{i}"
                            setup.append(f"let {arg_code} = {self._channel_sender_expr(var_name, clone=True)};")
                args.append(arg_code)

        # Look up mangled name from specialization map (scoped by current function)
        key = (self._current_function, ctx.getSourceInterval())
        mangled = self._specialization_map.get(key)
        if mangled:
            call = f"{mangled}({', '.join(args)})"
        else:
            call = f"{func_name}({', '.join(args)})"
        if setup:
            task = f"tokio::spawn({{ {' '.join(setup)} async move {{ {call}.await; }} }})"
        else:
            task = f"tokio::spawn(async move {{ {call}.await; }})"
        if self._spawn_handles_var:
            return f"{self._spawn_handles_var}.push({task});"
        return f"{task}.await.unwrap();"

    def visitChannelSendStatement(self, ctx: ZincParser.ChannelSendStatementContext) -> str:
        """Visit channel send statement."""
        channel_name = ctx.IDENTIFIER().getText()
        sender = self._channel_sender_expr(channel_name)
        value = self._render_channel_value(channel_name, ctx.expression())
        chan_info = self._channel_infos.get(channel_name)
        if chan_info and chan_info.is_bounded:
            return f"{sender}.send({value}).await.unwrap();"
        return f"{sender}.send({value}).unwrap();"

    def visitExpressionStatement(self, ctx: ZincParser.ExpressionStatementContext) -> str:
        """Visit expression statement."""
        expr = self.visit(ctx.expression())
        if expr.endswith(";"):
            return expr
        return f"{expr};"

    def visitStatement(self, ctx: ZincParser.StatementContext) -> str | None:
        """Visit a statement - dispatch to specific visitor."""
        return self.visitChildren(ctx)
