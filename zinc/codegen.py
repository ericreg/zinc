"""Code generation for the Zinc compiler."""

import re
from dataclasses import dataclass, field

from antlr4 import ParserRuleContext
from zinc.ast.types import (
    AnonymousStructTypeInfo,
    ArrayTypeInfo,
    BaseType,
    CallableTarget,
    CallableTypeInfo,
    ChannelTypeInfo,
    DictTypeInfo,
    OptionTypeInfo,
    ResultTypeInfo,
    SetTypeInfo,
    TupleTypeInfo,
    ValueTypeSpec,
    exact_type_to_rust,
    type_to_rust,
)
from zinc.atlas import (
    Atlas,
    ConstInstance,
    EnumInstance,
    FunctionInstance,
    StructFieldInfo,
    StructInstance,
    StructMethodInfo,
)
from zinc.meta_runtime import (
    COMPONENT_ORDER_QNAME,
    MetaListValue,
    MetaValue,
    is_meta_struct_qname,
    meta_struct_rust_name,
    metadata_runtime_definitions,
)
from zinc.modules import extract_identifier_path, struct_path_from_ctx
from zinc.numeric_literals import is_numeric_literal, numeric_literal_value
from zinc.parser.zincParser import zincParser as ZincParser
from zinc.parser.zincVisitor import zincVisitor
from zinc.string_literals import is_interpolated_string_literal, is_string_literal, to_rust_string_literal
from zinc.symbols import BoundArgument, BoundStructField, LexicalFunctionInfo, SymbolKind, SymbolTable


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
        lexical_functions: dict[str, LexicalFunctionInfo] | None = None,
        bound_call_args: dict[tuple[str | None, tuple[int, int]], list[BoundArgument]] | None = None,
        bound_struct_fields: dict[tuple[str | None, tuple[int, int]], list[BoundStructField]] | None = None,
    ):
        self.atlas = atlas
        self.module_graph = atlas.module_graph
        self.symbols = symbols
        self._specialization_map = specialization_map or {}  # (caller, interval) -> mangled
        self._channel_infos = channel_infos or {}  # var_name -> ChannelTypeInfo
        self._lexical_functions = lexical_functions or {}
        self._bound_call_args = bound_call_args or {}
        self._bound_struct_fields = bound_struct_fields or {}
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
        self._expected_result_type: BaseType | None = None
        self._expected_callable_info: CallableTypeInfo | None = None
        self._expected_dict_info: DictTypeInfo | None = None
        self._expected_set_info: SetTypeInfo | None = None
        self._expected_tuple_info: TupleTypeInfo | None = None
        self._spawn_handles_var: str | None = None
        self._select_counter = 0
        self._current_channel_params: set[str] = set()
        self._boxed_struct_vars: set[tuple[str | None, str]] = set()
        self._callable_signatures: dict[str, CallableTypeInfo] = {}
        self._anonymous_structs: dict[tuple, AnonymousStructTypeInfo] = {}
        self._captured_binding_names: set[str] = set()
        self._needs_metadata_runtime = False
        self._spread_temp_stack: list[dict[tuple[int, int], str]] = []

    def visit(self, tree):
        """Visit one parse node and post-process try-propagation sites."""
        rendered = super().visit(tree)
        if not isinstance(tree, ParserRuleContext) or not isinstance(rendered, str):
            return rendered
        if not isinstance(tree, ZincParser.ExpressionContext):
            return rendered
        family = self.symbols.auto_unwrap_family(tree.getSourceInterval(), self._current_function)
        if family in {BaseType.RESULT, BaseType.OPTION}:
            return f"({rendered})?"
        return rendered

    def generate(self) -> RustProgram:
        """Main entry point - generate Rust code for all reachable code."""
        # Pre-scan to determine which struct vars need mut
        self._prescan_for_mut_vars()
        self._collect_captured_binding_names()
        self._refine_function_return_callables()
        self._collect_callable_signatures()
        self._collect_anonymous_struct_types()
        self._mark_async_functions()

        imports = self._generate_imports()
        consts = [self._generate_const(c) for c in self.atlas.consts.values()]
        callable_enums = [self._generate_callable_enum(info) for _, info in sorted(self._callable_signatures.items())]
        closure_envs = [self._generate_closure_env_struct(info) for _, info in sorted(self._lexical_functions.items()) if info.finalized]
        anonymous_structs = [
            self._generate_anonymous_struct(info)
            for _, info in sorted(
                self._anonymous_structs.items(),
                key=lambda item: item[1].rust_type_name(),
            )
        ]
        functions = []
        main_body = []

        for func_name in self.atlas.topological_order():
            func = self.atlas.functions[func_name]
            if func.name == "main":
                if func.return_type == BaseType.RESULT and func.return_result_info is not None:
                    functions.append(self._generate_function_with_name(func, "__zinc_main", force_async=self._uses_async))
                    main_body = self._generate_result_main_wrapper_body()
                else:
                    self._current_function = func.mangled_name
                    self._current_module = func.module_id
                    self._declared_vars.clear()
                    self._current_channel_params = set()
                    main_body = self._generate_function_body(func)
            else:
                functions.append(self._generate_function(func))

        runtime_helpers = self._generate_runtime_helpers()
        structs = [
            *runtime_helpers,
            *closure_envs,
            *callable_enums,
            *anonymous_structs,
            *[self._generate_enum(e) for e in self.atlas.enums.values()],
            *[self._generate_struct(s) for s in self.atlas.structs.values()],
        ]

        return RustProgram(
            imports=imports,
            consts=consts,
            structs=structs,
            functions=functions,
            main_body=main_body,
            uses_async=self._uses_async,
        )

    def _callable_info_is_concrete(self, info: CallableTypeInfo | None) -> bool:
        """Return True when a callable signature contains no unknown slots."""
        if info is None:
            return False
        return all(param != BaseType.UNKNOWN for param in info.param_types) and info.return_type != BaseType.UNKNOWN

    def _refine_function_return_callables(self) -> None:
        """Refine abstract callable return signatures from concrete call sites."""
        for func in self.atlas.functions.values():
            if func.return_type != BaseType.CALLABLE or self._callable_info_is_concrete(func.return_callable_info):
                continue
            refined = self._concrete_callable_return_from_call_sites(func.mangled_name)
            if refined is not None:
                func.return_callable_info = refined

    def _concrete_callable_return_from_call_sites(self, mangled_name: str) -> CallableTypeInfo | None:
        """Find a concrete callable return signature for one function from its call sites."""
        resolved: CallableTypeInfo | None = None
        for (caller_name, interval), target_name in self._specialization_map.items():
            if target_name != mangled_name:
                continue
            symbol = self.symbols.lookup_by_interval(interval, caller_name)
            if symbol is None or not self._callable_info_is_concrete(symbol.callable_info):
                continue
            if resolved is None:
                resolved = symbol.callable_info.copy()
                continue
            if resolved.structural_key() == symbol.callable_info.structural_key():
                resolved = resolved.merge_targets_from(symbol.callable_info)
        return resolved

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

    def _collect_captured_binding_names(self) -> None:
        """Collect symbols that need shared cell storage for closure captures."""
        self._captured_binding_names = {symbol.unique_name for symbol in self.symbols.all_symbols() if symbol.is_captured_binding}

    def _prescan_block(self, block_ctx) -> None:
        """Recursively scan a block for struct assignments and method calls."""
        for stmt_ctx in block_ctx.statement():
            self._prescan_statement(stmt_ctx)

    def _prescan_statement(self, stmt_ctx) -> None:
        """Scan a statement for struct tracking and literal variable tracking."""
        # Track variable assignments of struct instances and literal values
        if stmt_ctx.typedVariableAssignment():
            var_ctx = stmt_ctx.typedVariableAssignment()
            var_names = [token.getText() for token in self._typed_assignment_tokens(var_ctx.typedAssignmentTarget())]
            expr = var_ctx.expression()
            struct_name = self._detect_struct_assignment(expr)
            if struct_name:
                for var_name in var_names:
                    self._struct_instance_vars[f"{self._current_function}:{var_name}"] = struct_name
            elif self._is_compile_time_literal_expr(expr):
                self._literal_vars.update(var_names)
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
        for expr_ctx in self._statement_expressions(stmt_ctx):
            self._walk_expression_if_blocks(expr_ctx, self._prescan_block)

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

    def _statement_expressions(self, stmt_ctx) -> list[ParserRuleContext]:
        """Collect the direct expression children of a statement."""
        expressions: list[ParserRuleContext] = []
        if stmt_ctx.typedVariableAssignment():
            expressions.append(stmt_ctx.typedVariableAssignment().expression())
        if stmt_ctx.variableAssignment():
            expressions.append(stmt_ctx.variableAssignment().expression())
        if stmt_ctx.expressionStatement():
            expressions.append(stmt_ctx.expressionStatement().expression())
        if stmt_ctx.returnStatement() and stmt_ctx.returnStatement().expression():
            expressions.append(stmt_ctx.returnStatement().expression())
        if stmt_ctx.channelSendStatement():
            expressions.append(stmt_ctx.channelSendStatement().expression())
        if stmt_ctx.ifStatement():
            expressions.extend(stmt_ctx.ifStatement().expression())
        if stmt_ctx.forStatement():
            expressions.append(stmt_ctx.forStatement().expression())
        if stmt_ctx.whileStatement():
            expressions.append(stmt_ctx.whileStatement().expression())
        if stmt_ctx.spawnStatement():
            expressions.append(stmt_ctx.spawnStatement().expression())
            if stmt_ctx.spawnStatement().argumentList():
                expressions.extend(self._raw_call_exprs(stmt_ctx.spawnStatement().argumentList()))
        return expressions

    def _walk_expression_if_blocks(self, node, visit_block) -> None:
        """Visit each block nested inside expression-form if subtrees."""
        if node is None:
            return
        if isinstance(node, ZincParser.IfExpressionContext):
            self._walk_expression_if_blocks(node.expression(), visit_block)
            visit_block(node.block(0))
            if len(node.block()) > 1:
                visit_block(node.block(1))
            if node.ifExpression():
                self._walk_expression_if_blocks(node.ifExpression(), visit_block)
            return
        if isinstance(node, ParserRuleContext):
            for i in range(node.getChildCount()):
                child = node.getChild(i)
                if isinstance(child, ParserRuleContext):
                    self._walk_expression_if_blocks(child, visit_block)

    def _prescan_callable_escapes(self, node) -> None:
        """Collect struct receivers whose bound methods escape as callable values."""
        if node is None:
            return
        if isinstance(node, ZincParser.MemberAccessExprContext) and self._current_function is not None:
            parent = node.parentCtx
            is_direct_call = isinstance(parent, ZincParser.FunctionCallExprContext) and parent.expression() is node
            if not is_direct_call:
                symbol = self.symbols.lookup_by_interval(node.getSourceInterval(), self._current_function)
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
        if isinstance(node, ZincParser.ForStatementContext):
            expr_symbol = self.symbols.lookup_by_interval(node.expression().getSourceInterval(), function_name)
            if expr_symbol and expr_symbol.resolved_type == BaseType.CHANNEL:
                return True
        if isinstance(node, ZincParser.ChannelReceiveExprContext):
            return True
        if isinstance(node, ZincParser.AwaitExprContext):
            return True
        if isinstance(node, ZincParser.ChannelSendStatementContext):
            return True
        if isinstance(node, ZincParser.SpawnStatementContext):
            return True
        if isinstance(node, ZincParser.FunctionCallExprContext):
            callee_name = self._function_call_name(node)
            if callee_name == "close":
                return False
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
        """Render the Rust channel value used for sends."""
        base = name
        return f"{base}.clone()" if clone else base

    def _channel_receiver_expr(self, name: str) -> str:
        """Render the Rust channel value used for receives."""
        return name

    def _render_channel_value(self, channel_name: str, expr_ctx) -> str:
        """Render a channel payload with the channel element type's ownership rules."""
        chan_info = self._channel_infos.get(channel_name)
        target_type = chan_info.element_type if chan_info else self._get_expr_type(expr_ctx)
        value = self._visit_expression_with_expectations(
            expr_ctx,
            expected_type=target_type,
            tuple_info=chan_info.element_tuple_info if chan_info else None,
            callable_info=chan_info.element_callable_info if chan_info else None,
            coerce_scalar=False,
            coerce_callable=False,
        )
        if target_type == BaseType.CALLABLE and chan_info and chan_info.element_callable_info:
            expr_symbol = self._get_expr_symbol(expr_ctx)
            if expr_symbol and expr_symbol.callable_info:
                if self._is_direct_callable_expr(expr_ctx, expr_symbol):
                    return self._render_callable_value_for_signature(
                        expr_symbol.callable_info,
                        chan_info.element_callable_info,
                    )
                return f"{value}.clone()"
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

    def _render_scoped_value_block(self, block_ctx) -> list[str]:
        """Render a value-producing block while keeping local bindings scoped."""
        previous_declared = set(self._declared_vars)
        try:
            return self._generate_value_block(block_ctx)
        finally:
            self._declared_vars = previous_declared

    def _append_block_lines(self, lines: list[str], stmts: list[str], indent: int) -> None:
        """Append rendered statements with a fixed indentation level."""
        prefix = "    " * indent
        for stmt in stmts:
            for line in stmt.split("\n"):
                lines.append(f"{prefix}{line}")

    def _append_rendered_statement(self, stmts: list[str], rendered) -> None:
        """Append a rendered statement or statement list to a block."""
        if not rendered:
            return
        if isinstance(rendered, list):
            stmts.extend(rendered)
        else:
            stmts.append(rendered)

    def _expected_type_for_expression(self, expr_ctx) -> BaseType | None:
        """Return the best result type expectation for an expression."""
        if self._expected_result_type not in {None, BaseType.UNKNOWN}:
            return self._expected_result_type
        expr_type = self._get_expr_type(expr_ctx)
        if expr_type != BaseType.UNKNOWN:
            return expr_type
        return None

    def _expected_callable_for_expression(self, expr_ctx) -> CallableTypeInfo | None:
        """Return the best callable expectation for an expression."""
        if self._expected_callable_info is not None:
            return self._expected_callable_info
        expr_symbol = self._get_expr_symbol(expr_ctx)
        if expr_symbol and expr_symbol.callable_info:
            return expr_symbol.callable_info
        return None

    def _coerce_rendered_value(
        self,
        value: str,
        expr_ctx,
        *,
        expected_type: BaseType | None = None,
        expected_callable_info: CallableTypeInfo | None = None,
        coerce_scalar: bool = True,
        coerce_callable: bool = True,
    ) -> str:
        """Coerce a rendered expression into the surrounding expected type."""
        resolved_expected_type = expected_type if expected_type is not None else self._expected_result_type
        resolved_callable_info = expected_callable_info if expected_callable_info is not None else self._expected_callable_info
        is_if_expression = isinstance(
            expr_ctx,
            (ZincParser.IfExprContext, ZincParser.IfExpressionContext),
        )

        if coerce_callable and not is_if_expression and resolved_expected_type == BaseType.CALLABLE and resolved_callable_info is not None:
            expr_symbol = self._get_expr_symbol(expr_ctx)
            if expr_symbol and expr_symbol.callable_info and self._is_direct_callable_expr(expr_ctx, expr_symbol):
                return self._render_callable_value_for_signature(
                    expr_symbol.callable_info,
                    resolved_callable_info,
                )

        if not coerce_scalar or is_if_expression:
            return value
        if resolved_expected_type == BaseType.STRING:
            return self._coerce_owned(value, BaseType.STRING, expr_ctx)
        if resolved_expected_type == BaseType.FLOAT and expr_ctx is not None:
            if self._get_expr_type(expr_ctx) == BaseType.INTEGER:
                return f"({value} as f64)"
        return value

    def _visit_expression_with_expectations(
        self,
        expr_ctx,
        *,
        expected_type: BaseType | None = None,
        dict_info: DictTypeInfo | None = None,
        set_info: SetTypeInfo | None = None,
        tuple_info: TupleTypeInfo | None = None,
        callable_info: CallableTypeInfo | None = None,
        coerce_scalar: bool = True,
        coerce_callable: bool = True,
    ) -> str:
        """Visit an expression with temporary expected result metadata."""
        previous_result_type = self._expected_result_type
        previous_callable_info = self._expected_callable_info
        previous_dict_info = self._expected_dict_info
        previous_set_info = self._expected_set_info
        previous_tuple_info = self._expected_tuple_info
        if expected_type is not None:
            self._expected_result_type = expected_type
        if callable_info is not None:
            self._expected_callable_info = callable_info
        if dict_info is not None:
            self._expected_dict_info = dict_info
        if set_info is not None:
            self._expected_set_info = set_info
        if tuple_info is not None:
            self._expected_tuple_info = tuple_info
        try:
            value = self.visit(expr_ctx)
        finally:
            self._expected_result_type = previous_result_type
            self._expected_callable_info = previous_callable_info
            self._expected_dict_info = previous_dict_info
            self._expected_set_info = previous_set_info
            self._expected_tuple_info = previous_tuple_info
        return self._coerce_rendered_value(
            value,
            expr_ctx,
            expected_type=expected_type,
            expected_callable_info=callable_info,
            coerce_scalar=coerce_scalar,
            coerce_callable=coerce_callable,
        )

    def _render_expression_value(self, expr_ctx) -> str:
        """Render a tail-position expression with the current expectations."""
        return self._coerce_rendered_value(self.visit(expr_ctx), expr_ctx)

    def _render_value_tail(self, stmt_ctx) -> list[str]:
        """Render the final statement of a value-producing block."""
        if stmt_ctx.expressionStatement():
            return [self._render_expression_value(stmt_ctx.expressionStatement().expression())]
        if stmt_ctx.block():
            return [self._render_value_block_expr(stmt_ctx.block())]
        if stmt_ctx.ifStatement():
            return [self._render_if_statement(stmt_ctx.ifStatement(), as_expression=True)]
        if stmt_ctx.returnStatement():
            return [self.visit(stmt_ctx.returnStatement())]
        if stmt_ctx.failStatement():
            return [self.visit(stmt_ctx.failStatement())]
        if stmt_ctx.breakStatement():
            return [self.visit(stmt_ctx.breakStatement())]
        if stmt_ctx.continueStatement():
            return [self.visit(stmt_ctx.continueStatement())]
        rendered = self.visit(stmt_ctx)
        if not rendered:
            return ["()"]
        return [rendered, "()"]

    def _generate_value_block(self, ctx: ZincParser.BlockContext) -> list[str]:
        """Generate statements for a block whose final statement yields a value."""
        statements = list(ctx.statement())
        if not statements:
            return ["()"]
        stmts: list[str] = []
        for stmt_ctx in statements[:-1]:
            self._append_rendered_statement(stmts, self.visit(stmt_ctx))
        stmts.extend(self._render_value_tail(statements[-1]))
        return stmts

    def _render_value_block_expr(self, block_ctx) -> str:
        """Render a value-producing block as a Rust block expression."""
        lines = ["{"]
        self._append_block_lines(lines, self._render_scoped_value_block(block_ctx), 1)
        lines.append("}")
        return "\n".join(lines)

    def _render_if_chain(
        self,
        conditions: list,
        blocks: list,
        else_block,
        *,
        as_expression: bool,
    ) -> str:
        """Render an if/else-if chain in statement or expression position."""
        lines: list[str] = []
        for i, expr_ctx in enumerate(conditions):
            cond = self.visit(expr_ctx)
            body_stmts = self._render_scoped_value_block(blocks[i]) if as_expression else self._render_scoped_block(blocks[i])
            keyword = "if" if i == 0 else "} else if"
            lines.append(f"{keyword} {cond} {{")
            self._append_block_lines(lines, body_stmts, 1)

        if else_block is not None:
            lines.append("} else {")
            else_stmts = self._render_scoped_value_block(else_block) if as_expression else self._render_scoped_block(else_block)
            self._append_block_lines(lines, else_stmts, 1)
        elif as_expression:
            lines.append("} else {")
            lines.append("    ()")

        lines.append("}")
        return "\n".join(lines)

    def _flatten_if_expression(self, ctx: ZincParser.IfExpressionContext) -> tuple[list, list, ParserRuleContext | None]:
        """Flatten nested expression-form else-if chains into a single sequence."""
        conditions = []
        blocks = []
        current = ctx
        else_block = None
        while current is not None:
            conditions.append(current.expression())
            blocks.append(current.block(0))
            if len(current.block()) > 1:
                else_block = current.block(1)
                break
            current = current.ifExpression()
        return conditions, blocks, else_block

    def _generate_imports(self) -> list[str]:
        """Generate import statements based on what's used."""
        imports = []
        collections: set[str] = set()
        needs_rc_refcell = bool(self._boxed_struct_vars)
        needs_arc_mutex = bool(self._captured_binding_names)
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
        if needs_arc_mutex:
            imports.append("use std::sync::{Arc, Mutex};")
        return imports

    def _generate_runtime_helpers(self) -> list[str]:
        """Generate built-in Rust helper types used by Zinc lowering."""
        channel_helper = "\n".join(
            [
                "enum __ZincTryRecv<T> {",
                "    Value(T),",
                "    Empty,",
                "    Closed,",
                "}",
                "",
                "enum __ZincTrySend<T> {",
                "    Sent,",
                "    Full(T),",
                "    Closed(T),",
                "}",
                "",
                "enum __ZincChannelSender<T> {",
                "    Bounded(tokio::sync::mpsc::Sender<T>),",
                "    Unbounded(tokio::sync::mpsc::UnboundedSender<T>),",
                "}",
                "",
                "enum __ZincChannelReceiver<T> {",
                "    Bounded(tokio::sync::mpsc::Receiver<T>),",
                "    Unbounded(tokio::sync::mpsc::UnboundedReceiver<T>),",
                "}",
                "",
                "impl<T> __ZincChannelReceiver<T> {",
                "    async fn recv(&mut self) -> Option<T> {",
                "        match self {",
                "            Self::Bounded(receiver) => receiver.recv().await,",
                "            Self::Unbounded(receiver) => receiver.recv().await,",
                "        }",
                "    }",
                "",
                "    fn try_recv(&mut self) -> __ZincTryRecv<T> {",
                "        match self {",
                "            Self::Bounded(receiver) => match receiver.try_recv() {",
                "                Ok(value) => __ZincTryRecv::Value(value),",
                "                Err(tokio::sync::mpsc::error::TryRecvError::Empty) => __ZincTryRecv::Empty,",
                "                Err(tokio::sync::mpsc::error::TryRecvError::Disconnected) => __ZincTryRecv::Closed,",
                "            },",
                "            Self::Unbounded(receiver) => match receiver.try_recv() {",
                "                Ok(value) => __ZincTryRecv::Value(value),",
                "                Err(tokio::sync::mpsc::error::TryRecvError::Empty) => __ZincTryRecv::Empty,",
                "                Err(tokio::sync::mpsc::error::TryRecvError::Disconnected) => __ZincTryRecv::Closed,",
                "            },",
                "        }",
                "    }",
                "}",
                "",
                "impl<T> Clone for __ZincChannelSender<T> {",
                "    fn clone(&self) -> Self {",
                "        match self {",
                "            Self::Bounded(sender) => Self::Bounded(sender.clone()),",
                "            Self::Unbounded(sender) => Self::Unbounded(sender.clone()),",
                "        }",
                "    }",
                "}",
                "",
                "struct __ZincChannel<T> {",
                "    sender: __ZincChannelSender<T>,",
                "    receiver: std::sync::Arc<tokio::sync::Mutex<__ZincChannelReceiver<T>>>,",
                "    closed: std::sync::Arc<std::sync::atomic::AtomicBool>,",
                "    close_notify: std::sync::Arc<tokio::sync::Notify>,",
                "}",
                "",
                "impl<T> Clone for __ZincChannel<T> {",
                "    fn clone(&self) -> Self {",
                "        Self {",
                "            sender: self.sender.clone(),",
                "            receiver: self.receiver.clone(),",
                "            closed: self.closed.clone(),",
                "            close_notify: self.close_notify.clone(),",
                "        }",
                "    }",
                "}",
                "",
                "impl<T: Send + 'static> __ZincChannel<T> {",
                "    fn bounded(capacity: i64) -> Self {",
                "        let (sender, receiver) = tokio::sync::mpsc::channel(capacity as usize);",
                "        Self {",
                "            sender: __ZincChannelSender::Bounded(sender),",
                "            receiver: std::sync::Arc::new(tokio::sync::Mutex::new(__ZincChannelReceiver::Bounded(receiver))),",
                "            closed: std::sync::Arc::new(std::sync::atomic::AtomicBool::new(false)),",
                "            close_notify: std::sync::Arc::new(tokio::sync::Notify::new()),",
                "        }",
                "    }",
                "",
                "    fn unbounded() -> Self {",
                "        let (sender, receiver) = tokio::sync::mpsc::unbounded_channel();",
                "        Self {",
                "            sender: __ZincChannelSender::Unbounded(sender),",
                "            receiver: std::sync::Arc::new(tokio::sync::Mutex::new(__ZincChannelReceiver::Unbounded(receiver))),",
                "            closed: std::sync::Arc::new(std::sync::atomic::AtomicBool::new(false)),",
                "            close_notify: std::sync::Arc::new(tokio::sync::Notify::new()),",
                "        }",
                "    }",
                "",
                "    async fn send(&self, value: T) {",
                "        if self.closed.load(std::sync::atomic::Ordering::SeqCst) {",
                '            panic!("send on closed channel");',
                "        }",
                "        match &self.sender {",
                "            __ZincChannelSender::Bounded(sender) => {",
                "                if let Err(_) = sender.send(value).await {",
                '                    panic!("send on closed channel");',
                "                }",
                "            },",
                "            __ZincChannelSender::Unbounded(sender) => {",
                "                if let Err(_) = sender.send(value) {",
                '                    panic!("send on closed channel");',
                "                }",
                "            },",
                "        }",
                "    }",
                "",
                "    fn try_send(&self, value: T) -> __ZincTrySend<T> {",
                "        if self.closed.load(std::sync::atomic::Ordering::SeqCst) {",
                "            return __ZincTrySend::Closed(value);",
                "        }",
                "        match &self.sender {",
                "            __ZincChannelSender::Bounded(sender) => match sender.try_send(value) {",
                "                Ok(()) => __ZincTrySend::Sent,",
                "                Err(tokio::sync::mpsc::error::TrySendError::Full(value)) => __ZincTrySend::Full(value),",
                "                Err(tokio::sync::mpsc::error::TrySendError::Closed(value)) => __ZincTrySend::Closed(value),",
                "            },",
                "            __ZincChannelSender::Unbounded(sender) => match sender.send(value) {",
                "                Ok(()) => __ZincTrySend::Sent,",
                "                Err(err) => __ZincTrySend::Closed(err.0),",
                "            },",
                "        }",
                "    }",
                "",
                "    fn close(&self) {",
                "        if self.closed.swap(true, std::sync::atomic::Ordering::SeqCst) {",
                '            panic!("double close");',
                "        }",
                "        self.close_notify.notify_waiters();",
                "    }",
                "",
                "    async fn recv_option(&self) -> Option<T> {",
                "        loop {",
                "            match self.receiver.clone().try_lock_owned() {",
                "                Ok(mut receiver) => match receiver.try_recv() {",
                "                    __ZincTryRecv::Value(value) => return Some(value),",
                "                    __ZincTryRecv::Closed => return None,",
                "                    __ZincTryRecv::Empty => {",
                "                        if self.closed.load(std::sync::atomic::Ordering::SeqCst) {",
                "                            return None;",
                "                        }",
                "                        let notified = self.close_notify.notified();",
                "                        drop(receiver);",
                "                        tokio::select! {",
                "                            value = async {",
                "                                let mut receiver = self.receiver.clone().lock_owned().await;",
                "                                receiver.recv().await",
                "                            } => return value,",
                "                            _ = notified => continue,",
                "                        }",
                "                    },",
                "                },",
                "                Err(_) => tokio::task::yield_now().await,",
                "            }",
                "        }",
                "    }",
                "",
                "    async fn recv(&self) -> T {",
                "        match self.recv_option().await {",
                "            Some(value) => value,",
                '            None => panic!("receive on closed channel"),',
                "        }",
                "    }",
                "",
                "    fn try_recv(&self) -> __ZincTryRecv<T> {",
                "        match self.receiver.clone().try_lock_owned() {",
                "            Ok(mut receiver) => match receiver.try_recv() {",
                "                __ZincTryRecv::Empty if self.closed.load(std::sync::atomic::Ordering::SeqCst) => __ZincTryRecv::Closed,",
                "                result => result,",
                "            },",
                "            Err(_) => __ZincTryRecv::Empty,",
                "        }",
                "    }",
                "}",
                "",
                "#[derive(Clone)]",
                "struct __ZincContext {",
                "    done: __ZincChannel<bool>,",
                "}",
                "",
                "impl Default for __ZincContext {",
                "    fn default() -> Self {",
                "        Self::background()",
                "    }",
                "}",
                "",
                "impl __ZincContext {",
                "    fn background() -> Self {",
                "        Self { done: __ZincChannel::unbounded() }",
                "    }",
                "",
                "    fn done(&self) -> __ZincChannel<bool> {",
                "        self.done.clone()",
                "    }",
                "",
                "    fn cancel(&self) {",
                "        self.done.close();",
                "    }",
                "}",
            ]
        )
        helpers = [channel_helper]
        if self._needs_metadata_runtime:
            helpers.extend(metadata_runtime_definitions())
        return helpers

    def _constant_value_for_expr(self, ctx):
        """Return the compile-time constant value recorded for an expression, if any."""
        symbol = self._get_expr_symbol(ctx)
        if symbol is None:
            return None
        return symbol.constant_value

    def _render_constant_value(self, value) -> str:
        """Render a compile-time constant directly into Rust."""
        if isinstance(value, MetaValue):
            return self._render_meta_value(value)
        if isinstance(value, MetaListValue):
            return self._render_meta_list(value)
        if isinstance(value, list):
            return f"vec![{', '.join(self._render_constant_value(item) for item in value)}]"
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, str):
            escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
            return f'String::from("{escaped}")'
        return repr(value)

    def _meta_list_element_rust_type(self, value: MetaListValue) -> str:
        """Return the Rust element type for a compile-time metadata list."""
        if is_meta_struct_qname(value.element_struct_qualified_name):
            return meta_struct_rust_name(value.element_struct_qualified_name)
        if value.element_struct_qualified_name == COMPONENT_ORDER_QNAME:
            return meta_struct_rust_name(value.element_struct_qualified_name)
        if value.element_exact_type is not None:
            return value.element_exact_type
        return type_to_rust(value.element_base_type)

    def _render_meta_list(self, value: MetaListValue) -> str:
        """Render a compile-time metadata list into a Rust Vec literal."""
        self._needs_metadata_runtime = True
        if not value.items:
            return f"Vec::<{self._meta_list_element_rust_type(value)}>::new()"
        return f"vec![{', '.join(self._render_constant_value(item) for item in value.items)}]"

    def _render_meta_value(self, value: MetaValue) -> str:
        """Render a compile-time metadata object into a Rust struct literal."""
        self._needs_metadata_runtime = True
        if value.struct_qualified_name == COMPONENT_ORDER_QNAME:
            name = str(value.fields.get("name", "depth_first"))
            variant = {
                "depth_first": "DepthFirst",
                "breadth_first": "BreadthFirst",
                "topological": "Topological",
            }.get(name, "DepthFirst")
            return f"__ZincComponentOrder::{variant}"
        rust_name = meta_struct_rust_name(value.struct_qualified_name)
        fields = []
        for field_name, field_value in value.fields.items():
            fields.append(f"{field_name}: {self._render_constant_value(field_value)}")
        return f"{rust_name} {{ {', '.join(fields)} }}"

    def _register_callable_info(self, info: CallableTypeInfo | None) -> None:
        """Collect a concrete callable signature and all nested callable signatures."""
        if info is None:
            return
        key = info.rust_type_name()
        existing = self._callable_signatures.get(key)
        if existing is None:
            self._callable_signatures[key] = info.copy()
        else:
            try:
                self._callable_signatures[key] = existing.merge_targets_from(info)
            except ValueError:

                def specificity(callable_info: CallableTypeInfo) -> int:
                    unknowns = sum(1 for base_type in callable_info.param_types if base_type == BaseType.UNKNOWN)
                    if callable_info.return_type == BaseType.UNKNOWN:
                        unknowns += 1
                    return unknowns

                chosen = existing if specificity(existing) <= specificity(info) else info
                self._callable_signatures[key] = chosen.copy()

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
            for channel_infos in func.arg_channel_infos.values():
                for channel_info in channel_infos:
                    self._register_callable_info(channel_info.element_callable_info)
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
        for channel_info in self._channel_infos.values():
            self._register_callable_info(channel_info.element_callable_info)
        self._prune_abstract_callable_signatures()

    def _register_anonymous_struct_info(self, info: AnonymousStructTypeInfo | None) -> None:
        """Collect a reachable anonymous-struct shape and any nested shapes."""
        if info is None:
            return
        key = info.structural_key()
        existing = self._anonymous_structs.get(key)
        if existing is None:
            self._anonymous_structs[key] = info.copy()
            existing = self._anonymous_structs[key]
        for field in existing.fields:
            self._register_type_metadata(
                field.resolved_type,
                array_info=field.array_info,
                dict_info=field.dict_info,
                set_info=field.set_info,
                tuple_info=field.tuple_info,
                callable_info=field.callable_info,
                struct_qualified_name=field.struct_qualified_name,
                anonymous_struct_info=field.anonymous_struct_info,
            )

    def _register_type_metadata(
        self,
        base_type: BaseType,
        *,
        array_info: ArrayTypeInfo | None = None,
        dict_info: DictTypeInfo | None = None,
        set_info: SetTypeInfo | None = None,
        tuple_info: TupleTypeInfo | None = None,
        callable_info: CallableTypeInfo | None = None,
        struct_qualified_name: str | None = None,
        anonymous_struct_info: AnonymousStructTypeInfo | None = None,
    ) -> None:
        """Recursively collect anonymous structs nested inside rich type metadata."""
        del struct_qualified_name  # Named structs are handled elsewhere; only anonymous shapes need synthesis.
        if base_type == BaseType.STRUCT:
            self._register_anonymous_struct_info(anonymous_struct_info)
            return
        if base_type == BaseType.ARRAY and array_info:
            self._register_type_metadata(
                array_info.element_type,
                tuple_info=array_info.element_tuple_info,
                callable_info=array_info.element_callable_info,
                struct_qualified_name=array_info.element_struct_qualified_name,
                anonymous_struct_info=array_info.element_anonymous_struct_info,
            )
            return
        if base_type == BaseType.DICT and dict_info:
            self._register_type_metadata(
                dict_info.key_type,
                callable_info=dict_info.key_callable_info,
                struct_qualified_name=dict_info.key_struct_qualified_name,
                anonymous_struct_info=dict_info.key_anonymous_struct_info,
            )
            self._register_type_metadata(
                dict_info.value_type,
                callable_info=dict_info.value_callable_info,
                struct_qualified_name=dict_info.value_struct_qualified_name,
                anonymous_struct_info=dict_info.value_anonymous_struct_info,
            )
            return
        if base_type == BaseType.SET and set_info:
            self._register_type_metadata(
                set_info.element_type,
                struct_qualified_name=set_info.element_struct_qualified_name,
                anonymous_struct_info=set_info.element_anonymous_struct_info,
            )
            return
        if base_type == BaseType.TUPLE and tuple_info:
            for index, element_type in enumerate(tuple_info.element_types):
                self._register_type_metadata(
                    element_type,
                    tuple_info=tuple_info.element_tuple_infos.get(index),
                    callable_info=tuple_info.element_callable_infos.get(index),
                    struct_qualified_name=tuple_info.element_struct_qualified_names.get(index),
                    anonymous_struct_info=tuple_info.element_anonymous_struct_infos.get(index),
                )
            return
        if base_type == BaseType.CALLABLE and callable_info:
            for index, param_type in enumerate(callable_info.param_types):
                self._register_type_metadata(
                    param_type,
                    array_info=callable_info.param_array_infos.get(index),
                    dict_info=callable_info.param_dict_infos.get(index),
                    set_info=callable_info.param_set_infos.get(index),
                    tuple_info=callable_info.param_tuple_infos.get(index),
                    callable_info=callable_info.param_callable_infos.get(index),
                    struct_qualified_name=callable_info.param_struct_qualified_names.get(index),
                    anonymous_struct_info=callable_info.param_anonymous_struct_infos.get(index),
                )
            self._register_type_metadata(
                callable_info.return_type,
                dict_info=callable_info.return_dict_info,
                set_info=callable_info.return_set_info,
                tuple_info=callable_info.return_tuple_info,
                callable_info=callable_info.return_callable_info,
                struct_qualified_name=callable_info.return_struct_qualified_name,
                anonymous_struct_info=callable_info.return_anonymous_struct_info,
            )

    def _collect_anonymous_struct_types(self) -> None:
        """Collect all reachable anonymous-struct shapes before Rust emission."""
        self._anonymous_structs = {}
        for struct in self.atlas.structs.values():
            for field in struct.fields:
                self._register_type_metadata(
                    field.resolved_type,
                    array_info=field.array_info,
                    dict_info=field.dict_info,
                    set_info=field.set_info,
                    tuple_info=field.tuple_info,
                    callable_info=field.callable_info,
                    struct_qualified_name=field.struct_qualified_name,
                    anonymous_struct_info=field.anonymous_struct_info,
                )
        for func in self.atlas.functions.values():
            for index, arg_type in enumerate(func.arg_types):
                self._register_type_metadata(
                    arg_type,
                    array_info=func.arg_array_infos.get(index),
                    dict_info=func.arg_dict_infos.get(index),
                    set_info=func.arg_set_infos.get(index),
                    tuple_info=func.arg_tuple_infos.get(index),
                    callable_info=func.arg_callable_infos.get(index),
                    struct_qualified_name=func.arg_struct_qualified_names.get(index),
                    anonymous_struct_info=func.arg_anonymous_struct_infos.get(index),
                )
            self._register_type_metadata(
                func.return_type,
                dict_info=func.return_dict_info,
                set_info=func.return_set_info,
                tuple_info=func.return_tuple_info,
                callable_info=func.return_callable_info,
                struct_qualified_name=func.return_struct_qualified_name,
                anonymous_struct_info=func.return_anonymous_struct_info,
            )
        for info in self._callable_signatures.values():
            self._register_type_metadata(
                BaseType.CALLABLE,
                callable_info=info,
            )
        for symbol in self.symbols.all_symbols():
            self._register_type_metadata(
                symbol.resolved_type,
                array_info=ArrayTypeInfo(
                    element_type=symbol.element_type,
                    element_tuple_info=symbol.tuple_info if symbol.element_type == BaseType.TUPLE else None,
                    element_callable_info=symbol.callable_info if symbol.element_type == BaseType.CALLABLE else None,
                    element_struct_qualified_name=symbol.element_struct_qualified_name,
                    element_anonymous_struct_info=symbol.element_anonymous_struct_info,
                )
                if symbol.resolved_type == BaseType.ARRAY and symbol.element_type is not None
                else None,
                dict_info=symbol.dict_info,
                set_info=symbol.set_info,
                tuple_info=symbol.tuple_info if symbol.resolved_type == BaseType.TUPLE else None,
                callable_info=symbol.callable_info if symbol.resolved_type == BaseType.CALLABLE else None,
                anonymous_struct_info=symbol.anonymous_struct_info,
            )
            if symbol.resolved_type == BaseType.ARRAY and symbol.element_type == BaseType.STRUCT:
                self._register_anonymous_struct_info(symbol.element_anonymous_struct_info)
        for channel_info in self._channel_infos.values():
            self._register_type_metadata(
                channel_info.element_type,
                tuple_info=channel_info.element_tuple_info,
                callable_info=channel_info.element_callable_info,
                struct_qualified_name=channel_info.element_struct_qualified_name,
                anonymous_struct_info=channel_info.element_anonymous_struct_info,
            )

    def _prune_abstract_callable_signatures(self) -> None:
        """Drop abstract callable signatures when a concrete version exists for the same target set."""
        grouped: dict[tuple[tuple, int], list[CallableTypeInfo]] = {}
        for info in self._callable_signatures.values():
            target_key = tuple(sorted(target.storage_key() for target in info.targets))
            grouped.setdefault((target_key, len(info.param_types)), []).append(info)

        keep: dict[str, CallableTypeInfo] = {}
        for infos in grouped.values():
            has_concrete = any(
                all(base_type != BaseType.UNKNOWN for base_type in info.param_types) and info.return_type != BaseType.UNKNOWN
                for info in infos
            )
            for info in infos:
                is_abstract = any(base_type == BaseType.UNKNOWN for base_type in info.param_types) or info.return_type == BaseType.UNKNOWN
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
        exact_type: str | None = None,
        array_info: ArrayTypeInfo | None = None,
        dict_info: DictTypeInfo | None = None,
        set_info: SetTypeInfo | None = None,
        tuple_info: TupleTypeInfo | None = None,
        callable_info: CallableTypeInfo | None = None,
        struct_qualified_name: str | None = None,
        anonymous_struct_info: AnonymousStructTypeInfo | None = None,
        result_info: ResultTypeInfo | None = None,
        option_info: OptionTypeInfo | None = None,
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
        if base_type == BaseType.STRUCT:
            if is_meta_struct_qname(struct_qualified_name):
                self._needs_metadata_runtime = True
                return meta_struct_rust_name(struct_qualified_name)
            if anonymous_struct_info:
                return anonymous_struct_info.rust_type_name()
            return self._named_struct_rust_name(struct_qualified_name)
        if base_type == BaseType.RESULT and result_info:
            return result_info.to_rust_type()
        if base_type == BaseType.OPTION and option_info:
            return option_info.to_rust_type()
        if base_type == BaseType.VOID:
            return "()"
        return exact_type_to_rust(exact_type, base_type)

    def _symbol_rust_type(self, symbol) -> str:
        """Render the full Rust type for a resolved symbol binding."""
        array_info = None
        if symbol.resolved_type == BaseType.ARRAY and symbol.element_type is not None:
            array_info = ArrayTypeInfo(
                element_type=symbol.element_type,
                element_exact_type=symbol.element_exact_type,
                element_tuple_info=symbol.tuple_info if symbol.element_type == BaseType.TUPLE else None,
                element_callable_info=symbol.callable_info if symbol.element_type == BaseType.CALLABLE else None,
                element_struct_qualified_name=symbol.element_struct_qualified_name,
                element_anonymous_struct_info=symbol.element_anonymous_struct_info,
                element_result_info=symbol.result_info if symbol.element_type == BaseType.RESULT else None,
                element_option_info=symbol.option_info if symbol.element_type == BaseType.OPTION else None,
            )
        return self._type_with_metadata_to_rust(
            symbol.resolved_type,
            exact_type=symbol.exact_type,
            array_info=array_info,
            dict_info=symbol.dict_info,
            set_info=symbol.set_info,
            tuple_info=symbol.tuple_info if symbol.resolved_type == BaseType.TUPLE else None,
            callable_info=symbol.callable_info if symbol.resolved_type == BaseType.CALLABLE else None,
            anonymous_struct_info=symbol.anonymous_struct_info,
            result_info=symbol.result_info if symbol.resolved_type == BaseType.RESULT else None,
            option_info=symbol.option_info if symbol.resolved_type == BaseType.OPTION else None,
        )

    def _callable_param_rust_type(self, info: CallableTypeInfo, index: int) -> str:
        """Render the Rust type for a callable parameter slot."""
        return self._type_with_metadata_to_rust(
            info.param_types[index],
            exact_type=info.param_exact_types[index] if index < len(info.param_exact_types) else None,
            array_info=info.param_array_infos.get(index),
            dict_info=info.param_dict_infos.get(index),
            set_info=info.param_set_infos.get(index),
            tuple_info=info.param_tuple_infos.get(index),
            callable_info=info.param_callable_infos.get(index),
            struct_qualified_name=info.param_struct_qualified_names.get(index),
            anonymous_struct_info=info.param_anonymous_struct_infos.get(index),
            result_info=info.param_result_infos.get(index),
            option_info=info.param_option_infos.get(index),
            as_reference=info.param_types[index] in {BaseType.ARRAY, BaseType.DICT, BaseType.SET},
        )

    def _callable_return_rust_type(self, info: CallableTypeInfo) -> str:
        """Render the Rust return type for a callable signature."""
        return self._type_with_metadata_to_rust(
            info.return_type,
            exact_type=info.return_exact_type,
            dict_info=info.return_dict_info,
            set_info=info.return_set_info,
            tuple_info=info.return_tuple_info,
            callable_info=info.return_callable_info,
            struct_qualified_name=info.return_struct_qualified_name,
            anonymous_struct_info=info.return_anonymous_struct_info,
            result_info=info.return_result_info,
            option_info=info.return_option_info,
            as_reference=False,
        )

    def _callable_dispatch_target(self, info: CallableTypeInfo, target: CallableTarget) -> str:
        """Render the Rust callable target for a dispatcher arm."""
        if target.kind in {"function", "lambda", "closure"}:
            return self.atlas._mangle_name(
                target.qualified_name,
                info.param_types,
                info.param_exact_types,
                arg_array_infos=info.param_array_infos,
                arg_dict_infos=info.param_dict_infos,
                arg_set_infos=info.param_set_infos,
                arg_tuple_infos=info.param_tuple_infos,
                arg_callable_infos=info.param_callable_infos,
                arg_result_infos=info.param_result_infos,
                arg_option_infos=info.param_option_infos,
                arg_struct_qualified_names=info.param_struct_qualified_names,
                arg_anonymous_struct_infos=info.param_anonymous_struct_infos,
            )
        if target.kind == "static_method":
            owner_qualified_name = target.receiver_struct_qualified_name or target.qualified_name.rpartition("::")[0]
            method_name = target.qualified_name.rpartition("::")[2]
            if owner_qualified_name in self.atlas.structs:
                return f"{self._struct_rust_name(self.atlas.structs[owner_qualified_name])}::{method_name}"
            if owner_qualified_name in self.atlas.enums:
                return f"{self._enum_rust_name(self.atlas.enums[owner_qualified_name])}::{method_name}"
            return f"{self.module_graph.rust_base_name(owner_qualified_name)}::{method_name}"
        if target.kind == "bound_method":
            return target.qualified_name.rpartition("::")[2]
        if target.kind == "context_cancel":
            return "context_cancel"
        raise KeyError(f"unknown callable target kind: {target.kind}")

    def _callable_variant_payload_type(self, target: CallableTarget) -> str | None:
        """Return the Rust payload type for a callable enum variant."""
        if target.kind == "context_cancel":
            return "__ZincContext"
        if target.kind == "closure":
            info = self._closure_info(target.qualified_name)
            if info is None:
                return None
            return self._closure_env_rust_name(info)
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
        lines.append("    Closed,")
        for target in ordered_targets:
            variant_name = self._callable_variant_name(info, target)
            payload_type = self._callable_variant_payload_type(target)
            if payload_type:
                lines.append(f"    {variant_name}({payload_type}),")
            else:
                lines.append(f"    {variant_name},")
        lines.append("}")
        lines.append("")
        lines.append(f"impl Default for {info.rust_type_name()} {{")
        lines.append("    fn default() -> Self {")
        lines.append("        Self::Closed")
        lines.append("    }")
        lines.append("}")
        lines.append("")
        lines.append(f"impl {info.rust_type_name()} {{")
        params = [f"arg_{index}: {self._callable_param_rust_type(info, index)}" for index in range(len(info.param_types))]
        ret_type = self._callable_return_rust_type(info)
        ret_suffix = "" if ret_type == "()" else f" -> {ret_type}"
        lines.append(f"    fn call(&self, {', '.join(params)}){ret_suffix} {{")
        lines.append("        match self {")
        lines.append('            Self::Closed => panic!("callable used after closed receive"),')
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
            elif target.kind == "context_cancel":
                call_expr = "ctx.cancel()"
                if ret_type == "()":
                    lines.append(f"            Self::{variant_name}(ctx) => {{ {call_expr}; }}")
                else:
                    lines.append(f"            Self::{variant_name}(ctx) => {call_expr},")
            else:
                callee = self._callable_dispatch_target(info, target)
                if target.kind == "closure":
                    call_expr = f"{callee}(env.clone(){', ' if args else ''}{args})"
                    if ret_type == "()":
                        lines.append(f"            Self::{variant_name}(env) => {{ {call_expr}; }}")
                    else:
                        lines.append(f"            Self::{variant_name}(env) => {call_expr},")
                else:
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
        if target.kind == "closure":
            closure_info = self._closure_info(target.qualified_name)
            if closure_info is None:
                return f"{info.rust_type_name()}::{variant_name}"
            return f"{info.rust_type_name()}::{variant_name}({self._closure_env_constructor(closure_info)})"
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
        if target.kind == "closure":
            closure_info = self._closure_info(target.qualified_name)
            if closure_info is None:
                return f"{expected_info.rust_type_name()}::{variant_name}"
            return f"{expected_info.rust_type_name()}::{variant_name}({self._closure_env_constructor(closure_info)})"
        return f"{expected_info.rust_type_name()}::{variant_name}"

    def _is_direct_callable_expr(self, expr_ctx, expr_symbol=None) -> bool:
        """Return True when an expression denotes a callable source, not an existing value."""
        symbol = expr_symbol or self._get_expr_symbol(expr_ctx)
        if symbol is None or symbol.resolved_type != BaseType.CALLABLE or symbol.callable_info is None:
            return False

        if isinstance(expr_ctx, ZincParser.LambdaExprContext):
            return True

        if isinstance(expr_ctx, ZincParser.PrimaryExprContext):
            primary = expr_ctx.primaryExpression()
            return bool(primary and primary.IDENTIFIER() and primary.IDENTIFIER().getText() not in self._declared_vars)

        if isinstance(expr_ctx, ZincParser.MemberAccessExprContext):
            is_direct_call = (
                isinstance(expr_ctx.parentCtx, ZincParser.FunctionCallExprContext) and expr_ctx.parentCtx.expression() is expr_ctx
            )
            if is_direct_call:
                return False

            if self._current_module is not None:
                path = extract_identifier_path(expr_ctx)
                if path:
                    if self.module_graph.resolve_function_path(self._current_module, path):
                        return True
                    static_target = self.module_graph.resolve_static_method_target(self._current_module, path)
                    if static_target is not None:
                        struct_symbol, method_name = static_target
                        struct = self.atlas.structs.get(struct_symbol.qualified_name)
                        if struct and any(m.name == method_name and m.is_static for m in struct.methods):
                            return True

            receiver_ctx = expr_ctx.expression()
            if isinstance(receiver_ctx, ZincParser.PrimaryExprContext):
                primary = receiver_ctx.primaryExpression()
                if primary and primary.IDENTIFIER():
                    receiver_name = primary.IDENTIFIER().getText()
                    key = f"{self._current_function}:{receiver_name}"
                    struct_name = self._struct_instance_vars.get(key)
                    struct = self.atlas.structs.get(struct_name) if struct_name else None
                    if struct and any(m.name == expr_ctx.IDENTIFIER().getText() for m in struct.methods):
                        return True

        return False

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
                arg_ctx = arg_ctxs[i] if arg_ctxs and i < len(arg_ctxs) else None
                if param_type == BaseType.STRING and (self._expr_is_string_literal(arg_ctx) or self._looks_like_rust_string_literal(arg)):
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
                    arg_symbol = self._get_expr_symbol(arg_ctx) if arg_ctx is not None else None
                    if arg_symbol and arg_symbol.callable_info and self._is_direct_callable_expr(arg_ctx, arg_symbol):
                        processed.append(
                            self._render_callable_value_for_signature(
                                arg_symbol.callable_info,
                                callable_info.param_callable_infos[i],
                            )
                        )
                    else:
                        processed.append(f"{arg}.clone()")
                elif param_type == BaseType.INTEGER and i < len(callable_info.param_exact_types):
                    exact_type = callable_info.param_exact_types[i]
                    if exact_type in {"i32", "i64"}:
                        processed.append(self._apply_literal_narrowing(arg, exact_type, arg_ctx))
                    else:
                        processed.append(arg)
                else:
                    processed.append(arg)
            else:
                processed.append(arg)
        return processed

    def _prepare_spawn_args(self, call_args: list, args: list[str]) -> tuple[list[str], list[str]]:
        """Clone channel arguments before entering the async move block."""
        setup: list[str] = []
        prepared: list[str] = []
        for i, arg_code in enumerate(args):
            arg_ctx = self._call_arg_expr(call_args[i]) if i < len(call_args) else None
            if arg_ctx is not None and self._get_expr_type(arg_ctx) == BaseType.CHANNEL:
                clone_name = f"__zinc_spawn_arg_{i}"
                setup.append(f"let {clone_name} = {arg_code}.clone();")
                prepared.append(clone_name)
            else:
                prepared.append(arg_code)
        return setup, prepared

    def _mark_async_functions(self) -> None:
        """Mark functions that need async because they spawn or call async functions."""
        async_funcs = {
            name for name, func in self.atlas.functions.items() if func.is_async or self._node_requires_async(func.ctx.block(), name)
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

    def _enum_rust_name(self, enum: EnumInstance) -> str:
        """Return the flattened Rust name for an enum."""
        return self.module_graph.rust_base_name(enum.qualified_name)

    def _named_struct_rust_name(self, qualified_name: str | None) -> str:
        """Return the flattened Rust name for a named struct qualified name."""
        if qualified_name is None:
            return "Struct"
        if is_meta_struct_qname(qualified_name):
            self._needs_metadata_runtime = True
            return meta_struct_rust_name(qualified_name)
        struct = self.atlas.structs.get(qualified_name)
        if struct is not None:
            return self._struct_rust_name(struct)
        return self.module_graph.rust_base_name(qualified_name)

    def _named_enum_rust_name(self, qualified_name: str | None) -> str:
        """Return the flattened Rust name for a named enum qualified name."""
        if qualified_name is None:
            return "Enum"
        if qualified_name == COMPONENT_ORDER_QNAME:
            self._needs_metadata_runtime = True
            return meta_struct_rust_name(qualified_name)
        enum = self.atlas.enums.get(qualified_name)
        if enum is not None:
            return self._enum_rust_name(enum)
        return self.module_graph.rust_base_name(qualified_name)

    def _const_rust_name(self, const: ConstInstance) -> str:
        """Return the flattened Rust name for a const."""
        return self.module_graph.rust_base_name(const.qualified_name).upper()

    def _sanitize_rust_identifier(self, text: str) -> str:
        """Return a Rust-safe identifier fragment."""
        cleaned = re.sub(r"[^0-9A-Za-z_]+", "_", text).strip("_")
        if not cleaned:
            cleaned = "value"
        if cleaned[0].isdigit():
            cleaned = f"v_{cleaned}"
        return cleaned

    def _rust_binding_name(self, unique_name: str) -> str:
        """Render the Rust variable name for a symbol unique name."""
        return f"__zv_{self._sanitize_rust_identifier(unique_name)}"

    def _closure_info(self, qualified_name: str) -> LexicalFunctionInfo | None:
        """Return lexical-function metadata for a qualified closure target."""
        return self._lexical_functions.get(qualified_name)

    def _closure_env_rust_name(self, info: LexicalFunctionInfo) -> str:
        """Return the synthesized Rust env type name for a lexical function."""
        return f"__ZincClosureEnv_{self._sanitize_rust_identifier(info.qualified_name)}"

    def _closure_capture_field_name(self, capture) -> str:
        """Return the env-struct field name for a capture."""
        return self._sanitize_rust_identifier(capture.name)

    def _closure_capture_inner_type(self, capture) -> str:
        """Return the Rust type stored inside a captured binding cell."""
        return self._type_with_metadata_to_rust(
            capture.resolved_type,
            array_info=ArrayTypeInfo(
                element_type=capture.element_type,
                element_tuple_info=capture.tuple_info if capture.element_type == BaseType.TUPLE else None,
                element_callable_info=capture.callable_info if capture.element_type == BaseType.CALLABLE else None,
                element_struct_qualified_name=capture.element_struct_qualified_name,
                element_anonymous_struct_info=capture.element_anonymous_struct_info,
            )
            if capture.resolved_type == BaseType.ARRAY and capture.element_type is not None
            else None,
            dict_info=capture.dict_info,
            set_info=capture.set_info,
            tuple_info=capture.tuple_info,
            callable_info=capture.callable_info,
            struct_qualified_name=capture.struct_qualified_name,
            anonymous_struct_info=capture.anonymous_struct_info,
            as_reference=False,
        )

    def _closure_capture_cell_type(self, capture) -> str:
        """Return the shared-cell Rust type for a captured binding."""
        return f"Arc<Mutex<{self._closure_capture_inner_type(capture)}>>"

    def _closure_env_constructor(self, info: LexicalFunctionInfo) -> str:
        """Construct an env literal from the currently visible captured bindings."""
        if not info.captures:
            return f"{self._closure_env_rust_name(info)} {{}}"
        fields = []
        for capture in info.captures:
            fields.append(f"{self._closure_capture_field_name(capture)}: {self._rust_binding_name(capture.binding_unique_name)}.clone()")
        return f"{self._closure_env_rust_name(info)} {{ {', '.join(fields)} }}"

    def _symbol_storage_unique_name(self, symbol) -> str | None:
        """Return the storage-bearing symbol unique name for a symbol or temp."""
        if symbol is None:
            return None
        if symbol.kind == SymbolKind.TEMPORARY and symbol.binding_unique_name is not None:
            return symbol.binding_unique_name
        if symbol.is_captured_ref:
            return symbol.unique_name
        return symbol.binding_unique_name or symbol.unique_name

    def _symbol_is_captured_cell(self, symbol) -> bool:
        """Return True when a symbol resolves to shared captured-cell storage."""
        storage_name = self._symbol_storage_unique_name(symbol)
        if storage_name is None:
            return False
        return storage_name in self._captured_binding_names or symbol.is_captured_ref

    def _render_captured_read(self, symbol) -> str:
        """Render a read from a captured binding cell."""
        storage_name = self._symbol_storage_unique_name(symbol)
        if storage_name is None:
            return "Default::default()"
        rust_name = self._rust_binding_name(storage_name)
        if symbol.resolved_type in {BaseType.INTEGER, BaseType.FLOAT, BaseType.BOOLEAN}:
            return f"*{rust_name}.lock().unwrap()"
        return f"{rust_name}.lock().unwrap().clone()"

    def _captured_binding_box_line(self, symbol, value_expr: str) -> str | None:
        """Return a boxing line for a captured binding introduced from a raw value."""
        if symbol is None or symbol.unique_name not in self._captured_binding_names:
            return None
        rust_name = self._rust_binding_name(symbol.unique_name)
        return f"let {rust_name} = Arc::new(Mutex::new({value_expr}));"

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
            type_str = self._type_with_metadata_to_rust(
                symbol.resolved_type,
                exact_type=symbol.exact_type,
                array_info=ArrayTypeInfo(
                    element_type=symbol.element_type,
                    element_exact_type=symbol.element_exact_type,
                    element_tuple_info=symbol.tuple_info if symbol.element_type == BaseType.TUPLE else None,
                    element_callable_info=symbol.callable_info if symbol.element_type == BaseType.CALLABLE else None,
                    element_struct_qualified_name=symbol.element_struct_qualified_name,
                    element_anonymous_struct_info=symbol.element_anonymous_struct_info,
                )
                if symbol.resolved_type == BaseType.ARRAY and symbol.element_type is not None
                else None,
                dict_info=symbol.dict_info,
                set_info=symbol.set_info,
                tuple_info=symbol.tuple_info if symbol.resolved_type == BaseType.TUPLE else None,
                callable_info=symbol.callable_info if symbol.resolved_type == BaseType.CALLABLE else None,
                anonymous_struct_info=symbol.anonymous_struct_info,
            )
            if type_str == "String":
                if self._expr_is_string_literal(ctx.expression()) or self._looks_like_rust_string_literal(value):
                    value = f"String::from({value})"
                return f"static {name}: std::sync::LazyLock<String> = std::sync::LazyLock::new(|| {value});"
            return f"const {name}: {type_str} = {value};"
        return f"const {name} = {value};"

    def _generate_anonymous_struct(self, info: AnonymousStructTypeInfo) -> str:
        """Generate a synthesized Rust struct for one anonymous shape."""
        lines = ["#[derive(Clone, Default)]", f"struct {info.rust_type_name()} {{"]
        for field in info.canonical_fields():
            rust_type = self._type_with_metadata_to_rust(
                field.resolved_type,
                exact_type=field.exact_type,
                array_info=field.array_info,
                dict_info=field.dict_info,
                set_info=field.set_info,
                tuple_info=field.tuple_info,
                callable_info=field.callable_info,
                struct_qualified_name=field.struct_qualified_name,
                anonymous_struct_info=field.anonymous_struct_info,
                as_reference=False,
            )
            lines.append(f"    {field.name}: {rust_type},")
        lines.append("}")
        return "\n".join(lines)

    def _generate_closure_env_struct(self, info: LexicalFunctionInfo) -> str:
        """Generate the hidden environment struct for one lexical function."""
        lines = ["#[derive(Clone)]", f"struct {self._closure_env_rust_name(info)} {{"]
        for capture in info.captures:
            lines.append(f"    {self._closure_capture_field_name(capture)}: {self._closure_capture_cell_type(capture)},")
        lines.append("}")
        return "\n".join(lines)

    def _generate_struct(self, struct: StructInstance) -> str:
        """Generate a struct definition and impl block."""
        if any(field.is_infer for field in struct.fields):
            return f"// infer-backed struct family {self._struct_rust_name(struct)} uses synthesized concrete shapes"
        lines = []
        rust_name = self._struct_rust_name(struct)

        # Struct definition
        lines.append(f"struct {rust_name} {{")
        for f in struct.fields:
            vis = "" if f.is_private else "pub "
            rust_type = f.rust_type()
            lines.append(f"    {vis}{f.name}: {rust_type},")
        lines.append("}")
        lines.append("")
        lines.append(f"impl Default for {rust_name} {{")
        lines.append("    fn default() -> Self {")
        field_defaults = ", ".join(f"{field.name}: {field.rust_default()}" for field in struct.fields)
        lines.append(f"        Self {{ {field_defaults} }}")
        lines.append("    }")
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

    def _generate_enum(self, enum: EnumInstance) -> str:
        """Generate an enum definition and optional static impl block."""
        lines = ["#[derive(Clone)]", f"enum {self._enum_rust_name(enum)} {{"]
        for variant in enum.variants:
            if variant.is_unit:
                lines.append(f"    {variant.name},")
                continue
            field_parts = []
            for field in variant.fields:
                rust_type = self._type_with_metadata_to_rust(
                    field.resolved_type,
                    exact_type=field.exact_type,
                    array_info=field.array_info,
                    dict_info=field.dict_info,
                    set_info=field.set_info,
                    tuple_info=field.tuple_info,
                    callable_info=field.callable_info,
                    struct_qualified_name=field.struct_qualified_name,
                    anonymous_struct_info=field.anonymous_struct_info,
                    as_reference=False,
                )
                field_parts.append(f"{field.name}: {rust_type}")
            lines.append(f"    {variant.name} {{ {', '.join(field_parts)} }},")
        lines.append("}")

        if enum.methods:
            lines.append("")
            lines.append(f"impl {self._enum_rust_name(enum)} {{")
            for method in enum.methods:
                method_code = self._generate_enum_method(method, enum)
                for line in method_code.split("\n"):
                    lines.append(f"    {line}")
            lines.append("}")

        return "\n".join(lines)

    def _generate_struct_method(self, method: StructMethodInfo, struct: StructInstance) -> str:
        """Generate a single struct method."""
        previous_declared = self._declared_vars.copy()
        previous_module = self._current_module
        previous_constructor_owner = self._current_constructor_owner
        self._current_module = struct.module_id
        if method.source_module_id is not None:
            self._current_module = method.source_module_id
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
        self._current_struct = struct.qualified_name
        self._current_struct_fields = {f.name: f for f in struct.fields}
        self._current_constructor_owner = method.constructor_owner_qualified_name or method.source_struct_qualified_name
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

    def _generate_enum_method(self, method: StructMethodInfo, enum: EnumInstance) -> str:
        """Generate a single static enum method."""
        previous_declared = self._declared_vars.copy()
        previous_module = self._current_module
        previous_constructor_owner = self._current_constructor_owner
        self._current_module = enum.module_id
        if method.source_module_id is not None:
            self._current_module = method.source_module_id
        self._declared_vars = {name for name, _, _ in method.parameters}

        param_strs = []
        for name, type_ann, resolved in method.parameters:
            if type_ann:
                param_strs.append(f"{name}: {self._zinc_type_to_rust(type_ann)}")
            elif resolved:
                param_strs.append(f"{name}: {resolved}")
            else:
                param_strs.append(f"{name}: i64")

        params = ", ".join(param_strs)
        ret_type = f" -> {method.return_type}" if method.return_type else ""

        self._current_struct = None
        self._current_struct_fields = None
        self._current_constructor_owner = method.constructor_owner_qualified_name or enum.qualified_name
        body_stmts = self._generate_block(method.body_ctx)
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
            "context": "__ZincContext",
        }
        lowered = zinc_type.lower()
        if lowered in mapping:
            return mapping[lowered]
        if zinc_type == "Self":
            return "Self"
        if self._current_module is not None:
            parts = zinc_type.split(".")
            struct_symbol = self.module_graph.resolve_struct_path(self._current_module, parts)
            if struct_symbol is not None:
                return self._named_struct_rust_name(struct_symbol.qualified_name)
            enum_symbol = self.module_graph.resolve_enum_path(self._current_module, parts)
            if enum_symbol is not None:
                return self._named_enum_rust_name(enum_symbol.qualified_name)
        return zinc_type

    def _generate_function(self, func: FunctionInstance) -> str:
        """Generate a function definition using mangled name."""
        return self._generate_function_with_name(func, func.mangled_name)

    def _generate_function_with_name(
        self,
        func: FunctionInstance,
        rust_name: str,
        *,
        force_async: bool | None = None,
    ) -> str:
        """Generate a function definition using a specific Rust name."""
        self._current_function = func.mangled_name
        self._current_module = func.module_id
        self._declared_vars.clear()
        self._current_channel_params = set()
        ctx = func.ctx
        lexical_info = self._closure_info(func.qualified_name)

        # Get parameter names and types from func.arg_types
        params = []
        param_prelude: list[str] = []
        if lexical_info is not None:
            params.append(f"__env: {self._closure_env_rust_name(lexical_info)}")
        if ctx.parameterList():
            for i, param_ctx in enumerate(ctx.parameterList().parameter()):
                param_name = param_ctx.IDENTIFIER().getText()
                if i < len(func.arg_types):
                    # Check if this is a channel parameter with type info
                    if i in func.arg_channel_infos and func.arg_channel_infos[i]:
                        # Use first channel info (all should have same element type)
                        chan_info = func.arg_channel_infos[i][0]
                        type_str = chan_info.to_rust_type()
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
                    elif func.arg_types[i] == BaseType.STRUCT:
                        type_str = self._type_with_metadata_to_rust(
                            BaseType.STRUCT,
                            struct_qualified_name=func.arg_struct_qualified_names.get(i),
                            anonymous_struct_info=func.arg_anonymous_struct_infos.get(i),
                            as_reference=False,
                        )
                    else:
                        type_str = self._type_with_metadata_to_rust(
                            func.arg_types[i],
                            exact_type=func.arg_exact_types[i] if i < len(func.arg_exact_types) else None,
                        )
                    params.append(f"{param_name}: {type_str}")
                else:
                    params.append(param_name)
                self._declared_vars.add(param_name)
                param_symbol = self._lookup_local_symbol(param_name)
                box_line = self._captured_binding_box_line(param_symbol, param_name)
                if box_line is not None:
                    param_prelude.append(box_line)

        body_stmts = self._generate_function_body(func)
        if param_prelude:
            body_stmts = [*param_prelude, *body_stmts]
        if lexical_info is not None:
            prelude = []
            for capture in lexical_info.captures:
                capture_symbol = self._lookup_captured_ref_symbol(capture.name)
                alias_unique_name = (
                    capture_symbol.unique_name if capture_symbol is not None else f"{self._current_function}.{capture.name}/capture"
                )
                alias_name = self._rust_binding_name(alias_unique_name)
                prelude.append(f"let {alias_name} = __env.{self._closure_capture_field_name(capture)}.clone();")
                self._declared_vars.add(capture.name)
            body_stmts = [*prelude, *body_stmts]
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
            elif func.return_type == BaseType.STRUCT:
                return_type_str = " -> " + self._type_with_metadata_to_rust(
                    BaseType.STRUCT,
                    struct_qualified_name=func.return_struct_qualified_name,
                    anonymous_struct_info=func.return_anonymous_struct_info,
                    as_reference=False,
                )
            elif func.return_type == BaseType.RESULT and func.return_result_info:
                return_type_str = f" -> {func.return_result_info.to_rust_type()}"
            elif func.return_type == BaseType.OPTION and func.return_option_info:
                return_type_str = f" -> {func.return_option_info.to_rust_type()}"
            else:
                return_type_str = " -> " + self._type_with_metadata_to_rust(
                    func.return_type,
                    exact_type=func.return_exact_type,
                )
        else:
            return_type_str = ""

        async_kw = "async " if (func.is_async if force_async is None else force_async) else ""
        lines = [f"{async_kw}fn {rust_name}({param_str}){return_type_str} {{"]
        for stmt in body_stmts:
            # Handle multiline statements (like for loops, if/else) by indenting each line
            for line in stmt.split("\n"):
                lines.append(f"    {line}")
        lines.append("}")

        return "\n".join(lines)

    def _generate_result_main_wrapper_body(self) -> list[str]:
        """Generate the outer Rust main wrapper for Zinc mains that return Result."""
        call = "__zinc_main().await" if self._uses_async else "__zinc_main()"
        return [
            f"if let Err(err) = {call} {{",
            '    eprintln!("{}", err);',
            "    std::process::exit(1);",
            "}",
        ]

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
            for expr_ctx in self._statement_expressions(stmt):
                if self._expression_if_blocks_contain_spawn(expr_ctx):
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

    def _expression_if_blocks_contain_spawn(self, expr_ctx) -> bool:
        """Return True when an expression-form if subtree contains a spawn."""
        found = False

        def visit_block(block_ctx) -> None:
            nonlocal found
            if not found and self._block_contains_spawn(block_ctx):
                found = True

        self._walk_expression_if_blocks(expr_ctx, visit_block)
        return found

    def _render_spawn_handle_awaits(self, handle_var: str) -> str:
        """Render code that waits for all spawned tasks in this function."""
        return "\n".join(
            [
                f"while let Some(__zinc_spawn_handle) = {handle_var}.pop() {{",
                "    __zinc_spawn_handle.await.unwrap();",
                "}",
            ]
        )

    def _generate_block(self, ctx: ZincParser.BlockContext) -> list[str]:
        """Generate statements for a block."""
        stmts = []
        for stmt_ctx in ctx.statement():
            self._append_rendered_statement(stmts, self.visit(stmt_ctx))
        return stmts

    def _indent(self, text: str) -> str:
        """Add current indentation to text."""
        indent = "    " * self._indent_level
        return f"{indent}{text}"

    def _expr_is_string_literal(self, ctx) -> bool:
        """Return True when an expression is a direct Zinc string literal."""
        if not isinstance(ctx, ZincParser.PrimaryExprContext):
            return False
        primary = ctx.primaryExpression()
        if not primary or not primary.literal():
            return False
        return is_string_literal(primary.literal().getText())

    def _looks_like_rust_string_literal(self, value: str) -> bool:
        """Return True when rendered Rust code is definitely a string literal."""
        return value.startswith('"') or value.startswith('r"') or bool(re.match(r"^r#+\"", value))

    def _call_key(self, ctx) -> tuple[str | None, tuple[int, int]]:
        """Return the scoped call-site key shared with semantic analysis."""
        return (self._current_function, ctx.getSourceInterval())

    def _raw_call_exprs(self, argument_list_ctx) -> list:
        """Return call argument expressions in written order."""
        if argument_list_ctx is None:
            return []
        return [arg_ctx.expression() for arg_ctx in argument_list_ctx.argument()]

    def _call_args_for_ctx(self, ctx) -> list:
        """Return bound call arguments when available, otherwise raw expressions."""
        return self._bound_call_args.get(self._call_key(ctx)) or self._raw_call_exprs(ctx.argumentList())

    def _struct_fields_for_ctx(self, ctx) -> list[BoundStructField]:
        """Return bound struct literal fields in final last-wins form."""
        return self._bound_struct_fields.get(self._call_key(ctx), [])

    def _raw_struct_literal_fields(self, ctx) -> tuple[dict[str, tuple[str, ParserRuleContext]], bool]:
        """Render explicit struct fields directly when semantic binding is unavailable."""
        fields: dict[str, tuple[str, ParserRuleContext]] = {}
        has_spread = False
        for entry_ctx in ctx.structFieldEntry():
            if entry_ctx.fieldSpread() is not None:
                has_spread = True
                continue
            field_ctx = entry_ctx.fieldInit()
            field_name = field_ctx.IDENTIFIER().getText()
            fields[field_name] = (self.visit(field_ctx.expression()), field_ctx.expression())
        return fields, has_spread

    def _call_arg_expr(self, arg) -> object:
        """Return the parse expression for a raw or bound call argument."""
        if isinstance(arg, BoundArgument) and arg.spread_field_name is not None:
            return None
        return arg.expression if isinstance(arg, BoundArgument) else arg

    def _spread_source_key(self, expr_ctx: ParserRuleContext) -> tuple[int, int]:
        """Return a stable key for one spread source expression."""
        return expr_ctx.getSourceInterval()

    def _simple_spread_source(self, expr_ctx) -> bool:
        """Return True when repeating a spread source cannot repeat side effects."""
        if isinstance(expr_ctx, ZincParser.PrimaryExprContext):
            primary = expr_ctx.primaryExpression()
            return bool(primary and (primary.IDENTIFIER() or primary.getText() == "self"))
        if isinstance(expr_ctx, ZincParser.MemberAccessExprContext):
            return self._simple_spread_source(expr_ctx.expression())
        return False

    def _prepare_spread_temps(self, items: list, prefix: str) -> tuple[list[str], dict[tuple[int, int], str]]:
        """Stage repeated nontrivial spread sources once for a call or struct literal."""
        sources: dict[tuple[int, int], ParserRuleContext] = {}
        counts: dict[tuple[int, int], int] = {}
        for item in items:
            source_expr = getattr(item, "spread_source_expr", None)
            if source_expr is None:
                continue
            key = self._spread_source_key(source_expr)
            sources.setdefault(key, source_expr)
            counts[key] = counts.get(key, 0) + 1

        lines: list[str] = []
        temps: dict[tuple[int, int], str] = {}
        for key, count in counts.items():
            source_expr = sources[key]
            if count <= 1 or self._simple_spread_source(source_expr):
                continue
            temp_name = self._staged_temp_name(prefix, source_expr)
            temps[key] = temp_name
            lines.append(f"let {temp_name} = {self.visit(source_expr)};")
        return lines, temps

    def _wrap_spread_temps(self, value: str, setup: list[str]) -> str:
        """Wrap an expression in a Rust block that stages spread sources."""
        if not setup:
            return value
        lines = ["{", *[f"    {line}" for line in setup], f"    {value}", "}"]
        return "\n".join(lines)

    def _spread_source_value(self, source_expr) -> str:
        """Render a spread source, using a staged temporary when one is active."""
        key = self._spread_source_key(source_expr)
        for mapping in reversed(self._spread_temp_stack):
            if key in mapping:
                return mapping[key]
        rendered = self.visit(source_expr)
        if self._simple_spread_source(source_expr):
            return rendered
        return f"({rendered})"

    def _spread_field_needs_clone(self, value_type: BaseType) -> bool:
        """Return True for field values that should be cloned out of a spread source."""
        return value_type in {
            BaseType.STRING,
            BaseType.ARRAY,
            BaseType.DICT,
            BaseType.SET,
            BaseType.TUPLE,
            BaseType.CALLABLE,
            BaseType.STRUCT,
            BaseType.RESULT,
            BaseType.OPTION,
        }

    def _render_spread_field_value(
        self,
        source_expr,
        field_name: str,
        value_info,
        *,
        expected_type: BaseType | None = None,
    ) -> str:
        """Render one field contributed by a spread source."""
        value = f"{self._spread_source_value(source_expr)}.{field_name}"
        if self._spread_field_needs_clone(value_info.base_type):
            value = f"{value}.clone()"
        if expected_type == BaseType.FLOAT and value_info.base_type == BaseType.INTEGER:
            return f"({value} as f64)"
        return value

    def _render_bound_struct_field(
        self,
        bound_field: BoundStructField,
        *,
        expected_type: BaseType | None = None,
    ) -> str:
        """Render one final struct literal field value."""
        if bound_field.spread_field_name is not None:
            return self._render_spread_field_value(
                bound_field.spread_source_expr,
                bound_field.spread_field_name,
                bound_field.value_info,
                expected_type=expected_type,
            )
        value = self.visit(bound_field.expression)
        if expected_type == BaseType.FLOAT and bound_field.value_info.base_type == BaseType.INTEGER:
            return f"({value} as f64)"
        return value

    def _with_default_module(self, arg, render):
        """Render a default argument in its declaration module."""
        if not isinstance(arg, BoundArgument) or not arg.is_default or arg.owner_module_id is None:
            return render()
        previous_module = self._current_module
        self._current_module = arg.owner_module_id
        try:
            return render()
        finally:
            self._current_module = previous_module

    def _visit_call_arg(self, arg) -> str:
        """Visit a raw or bound call argument."""
        if isinstance(arg, BoundArgument) and arg.spread_field_name is not None:
            return self._render_spread_field_value(arg.spread_source_expr, arg.spread_field_name, arg.value_info)
        return self._with_default_module(arg, lambda: self.visit(self._call_arg_expr(arg)))

    def _visit_call_arg_with_expectations(self, arg, **kwargs) -> str:
        """Visit a raw or bound call argument with expected type metadata."""
        if isinstance(arg, BoundArgument) and arg.spread_field_name is not None:
            return self._render_spread_field_value(
                arg.spread_source_expr,
                arg.spread_field_name,
                arg.value_info,
                expected_type=kwargs.get("expected_type"),
            )
        return self._with_default_module(
            arg,
            lambda: self._visit_expression_with_expectations(self._call_arg_expr(arg), **kwargs),
        )

    # --- Expression Visitors (return Rust code strings) ---

    def visitLiteral(self, ctx: ZincParser.LiteralContext) -> str:
        """Visit a literal value."""
        text = ctx.getText()
        if is_interpolated_string_literal(text):
            return self._render_interpolated_string(text)
        if is_string_literal(text):
            return to_rust_string_literal(text)
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
                owner_symbol, method_name = static_target
                if owner_symbol.kind == "struct":
                    struct = self.atlas.structs.get(owner_symbol.qualified_name)
                    if struct:
                        return f"{self._struct_rust_name(struct)}::{method_name}"
                if owner_symbol.kind == "enum":
                    enum = self.atlas.enums.get(owner_symbol.qualified_name)
                    if enum:
                        return f"{self._enum_rust_name(enum)}::{method_name}"
                return f"{self.module_graph.rust_base_name(owner_symbol.qualified_name)}::{method_name}"

            enum_variant = self.module_graph.resolve_enum_variant_path(self._current_module, parts)
            if enum_variant:
                enum_symbol, variant_name = enum_variant
                return f"{self._named_enum_rust_name(enum_symbol.qualified_name)}::{variant_name}"

            enum_symbol = self.module_graph.resolve_enum_path(self._current_module, parts)
            if enum_symbol:
                return self._named_enum_rust_name(enum_symbol.qualified_name)

            return token

        return re.sub(r"\b[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*\b", replace, expr)

    def visitPrimaryExpression(self, ctx: ZincParser.PrimaryExpressionContext) -> str:
        """Visit a primary expression."""
        if hasattr(ctx, "builtinTypeQuery") and ctx.builtinTypeQuery():
            constant_value = self._constant_value_for_expr(ctx)
            if constant_value is not None:
                return self._render_constant_value(constant_value)
        if ctx.literal():
            return self.visit(ctx.literal())
        if hasattr(ctx, "unitLiteral") and ctx.unitLiteral():
            return "()"
        if hasattr(ctx, "anonymousStructLiteral") and ctx.anonymousStructLiteral():
            return self.visit(ctx.anonymousStructLiteral())
        if hasattr(ctx, "builtinResultOptionConstructor") and ctx.builtinResultOptionConstructor():
            ctor = ctx.builtinResultOptionConstructor()
            if ctor.NONE():
                return "None"
            inner_expr = ctor.expression()
            inner = self.visit(inner_expr)
            expr_symbol = self._get_expr_symbol(ctx)
            if ctor.OK():
                target_spec = expr_symbol.result_info.ok_type if expr_symbol and expr_symbol.result_info else None
                inner = self._coerce_to_value_spec(inner, target_spec, inner_expr)
                return f"Ok({inner})"
            if ctor.ERR():
                target_spec = expr_symbol.result_info.err_type if expr_symbol and expr_symbol.result_info else None
                inner = self._coerce_to_value_spec(inner, target_spec, inner_expr)
                return f"Err({inner})"
            target_spec = expr_symbol.option_info.some_type if expr_symbol and expr_symbol.option_info else None
            inner = self._coerce_to_value_spec(inner, target_spec, inner_expr)
            return f"Some({inner})"
        name_token = ctx.IDENTIFIER() or (ctx.TYPE_KW() if hasattr(ctx, "TYPE_KW") else None)
        if name_token:
            name = name_token.getText()
            expr_symbol = self._get_expr_symbol(ctx)
            is_direct_call = (
                isinstance(ctx.parentCtx, ZincParser.PrimaryExprContext)
                and isinstance(ctx.parentCtx.parentCtx, ZincParser.FunctionCallExprContext)
                and ctx.parentCtx.parentCtx.expression() is ctx.parentCtx
            )
            if expr_symbol and expr_symbol.resolved_type == BaseType.CALLABLE and name not in self._declared_vars and not is_direct_call:
                return self._render_callable_value(expr_symbol.callable_info)
            if expr_symbol and self._symbol_is_captured_cell(expr_symbol):
                return self._render_captured_read(expr_symbol)
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
        if ctx.enumVariantConstruction():
            return self.visit(ctx.enumVariantConstruction())
        if ctx.structInstantiation():
            return self.visit(ctx.structInstantiation())
        if ctx.getText() == "self":
            return "self"
        if ctx.expression():
            return f"({self.visit(ctx.expression())})"
        return ctx.getText()

    def visitAnonymousStructLiteral(self, ctx) -> str:
        """Visit an anonymous struct literal."""
        expr_symbol = self._get_expr_symbol(ctx)
        anonymous_struct_info = expr_symbol.anonymous_struct_info if expr_symbol else None
        struct_name = anonymous_struct_info.rust_type_name() if anonymous_struct_info else "__ZincAnonStruct_missing"
        field_info_map = anonymous_struct_info.field_map() if anonymous_struct_info else {}
        bound_fields = self._struct_fields_for_ctx(ctx)
        if not bound_fields:
            raw_fields, has_spread = self._raw_struct_literal_fields(ctx)
            if has_spread:
                raise RuntimeError("internal error: struct spread was not bound during semantic analysis")
            fields = []
            for field_name, (field_value, expr_ctx) in raw_fields.items():
                field_info = field_info_map.get(field_name)
                if field_info is not None:
                    field_value = self._coerce_owned(field_value, field_info.resolved_type, expr_ctx)
                fields.append(f"{field_name}: {field_value}")
            return f"{struct_name} {{ {', '.join(fields)} }}"
        spread_setup, spread_temps = self._prepare_spread_temps(bound_fields, "field_spread")
        self._spread_temp_stack.append(spread_temps)
        fields = []
        for bound_field in bound_fields:
            field_name = bound_field.name
            field_value = self._render_bound_struct_field(bound_field)
            field_info = field_info_map.get(field_name)
            if field_info is not None:
                field_value = self._coerce_owned(
                    field_value,
                    field_info.resolved_type,
                    None if bound_field.spread_source_expr is not None else bound_field.expression,
                )
            fields.append(f"{field_name}: {field_value}")
        self._spread_temp_stack.pop()
        return self._wrap_spread_temps(f"{struct_name} {{ {', '.join(fields)} }}", spread_setup)

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
            target_type = info.element_types[i] if i < len(info.element_types) else self._get_expr_type(expr_ctx)
            value = self._visit_expression_with_expectations(
                expr_ctx,
                expected_type=target_type,
                tuple_info=info.element_tuple_infos.get(i),
                callable_info=info.element_callable_infos.get(i),
                coerce_scalar=False,
                coerce_callable=False,
            )
            elements.append(self._coerce_owned(value, target_type, expr_ctx))
        if len(elements) == 1:
            return f"({elements[0]},)"
        return f"({', '.join(elements)})"

    def visitAdditiveExpr(self, ctx: ZincParser.AdditiveExprContext) -> str:
        """Visit addition/subtraction expression."""
        left = self.visit(ctx.expression(0))
        op = ctx.getChild(1).getText()
        right = self.visit(ctx.expression(1))
        left, right = self._promote_numeric_operands(
            left,
            ctx.expression(0),
            right,
            ctx.expression(1),
        )

        return f"({left} {op} {right})"

    def visitMultiplicativeExpr(self, ctx: ZincParser.MultiplicativeExprContext) -> str:
        """Visit multiplication/division expression."""
        left = self.visit(ctx.expression(0))
        op = ctx.getChild(1).getText()
        right = self.visit(ctx.expression(1))
        left, right = self._promote_numeric_operands(
            left,
            ctx.expression(0),
            right,
            ctx.expression(1),
        )

        return f"({left} {op} {right})"

    def visitPowerExpr(self, ctx: ZincParser.PowerExprContext) -> str:
        """Visit exponentiation expression."""
        left = self.visit(ctx.expression(0))
        right = self.visit(ctx.expression(1))
        return self._render_power_expr(left, ctx.expression(0), right, ctx.expression(1), ctx)

    def _get_expr_type(self, ctx) -> BaseType:
        """Get the resolved type of an expression from the symbol table or atlas."""
        # Special handling for function calls - look up return type from atlas
        if isinstance(ctx, ZincParser.FunctionCallExprContext):
            key = (self._current_function, ctx.getSourceInterval())
            mangled = self._specialization_map.get(key)
            if mangled and mangled in self.atlas.functions:
                return self.atlas.functions[mangled].return_type

        symbol = self.symbols.lookup_by_interval(ctx.getSourceInterval(), self._current_function)
        if symbol:
            return symbol.resolved_type
        return BaseType.UNKNOWN

    def _get_expr_exact_type(self, ctx) -> str | None:
        """Get the resolved exact scalar type for an expression, when known."""
        if isinstance(ctx, ZincParser.FunctionCallExprContext):
            key = (self._current_function, ctx.getSourceInterval())
            mangled = self._specialization_map.get(key)
            if mangled and mangled in self.atlas.functions:
                return self.atlas.functions[mangled].return_exact_type

        symbol = self.symbols.lookup_by_interval(ctx.getSourceInterval(), self._current_function)
        if symbol:
            return symbol.exact_type
        return None

    def _promote_numeric_operands(self, left: str, left_ctx, right: str, right_ctx) -> tuple[str, str]:
        """Cast mixed int/float operands to the float operand's exact type."""
        left_type = self._get_expr_type(left_ctx)
        right_type = self._get_expr_type(right_ctx)

        if left_type == BaseType.INTEGER and right_type == BaseType.FLOAT:
            float_exact = exact_type_to_rust(self._get_expr_exact_type(right_ctx), BaseType.FLOAT)
            return f"({left} as {float_exact})", right
        if left_type == BaseType.FLOAT and right_type == BaseType.INTEGER:
            float_exact = exact_type_to_rust(self._get_expr_exact_type(left_ctx), BaseType.FLOAT)
            return left, f"({right} as {float_exact})"
        return left, right

    def _coerce_numeric_rhs_for_target(self, value: str, value_ctx, target_type: BaseType, target_exact_type: str | None) -> str:
        """Cast integer RHS values when mutating a float target."""
        value_type = self._get_expr_type(value_ctx)
        if target_type == BaseType.FLOAT and value_type == BaseType.INTEGER:
            float_exact = exact_type_to_rust(target_exact_type, BaseType.FLOAT)
            return f"({value} as {float_exact})"
        return value

    def _render_power_expr(self, left: str, left_ctx, right: str, right_ctx, result_ctx) -> str:
        """Render Zinc exponentiation to Rust pow/powf calls."""
        result_type = self._get_expr_type(result_ctx)
        if result_type == BaseType.FLOAT:
            float_exact = exact_type_to_rust(self._get_expr_exact_type(result_ctx), BaseType.FLOAT)
            left_type = self._get_expr_type(left_ctx)
            right_type = self._get_expr_type(right_ctx)
            if left_type == BaseType.INTEGER:
                left = f"({left} as {float_exact})"
            if right_type == BaseType.INTEGER:
                right = f"({right} as {float_exact})"
            return f"({left}).powf({right})"
        int_exact = exact_type_to_rust(self._get_expr_exact_type(result_ctx), BaseType.INTEGER)
        return f"({left} as {int_exact}).pow(({right}) as u32)"

    def _get_expr_symbol(self, ctx):
        """Get the resolved symbol for an expression-like context."""
        symbol = self.symbols.lookup_by_interval(ctx.getSourceInterval(), self._current_function)
        if symbol is not None:
            return symbol
        if isinstance(ctx, ZincParser.LambdaExprContext):
            return self.symbols.lookup_by_interval(ctx.lambdaExpression().getSourceInterval(), self._current_function)
        return None

    def _lookup_local_symbol(self, name: str):
        """Look up the latest resolved local/parameter symbol in the current function."""
        prefix = f"{self._current_function}."
        matches = [symbol for symbol in self.symbols.all_symbols() if symbol.id == name and symbol.unique_name.startswith(prefix)]
        return matches[-1] if matches else None

    def _lookup_identifier_symbol(self, name: str):
        """Resolve an identifier name to the nearest local symbol, if any."""
        symbol = self._lookup_local_symbol(name)
        if symbol is not None:
            return symbol
        return self.symbols.lookup_by_id(name)

    def _staged_temp_name(self, prefix: str, ctx: ParserRuleContext) -> str:
        """Build a stable temporary name for staged expression evaluation."""
        start, stop = ctx.getSourceInterval()
        return f"__zinc_{prefix}_{start}_{stop}"

    def _lookup_captured_ref_symbol(self, name: str):
        """Return the closure-local captured-ref symbol for a given source name."""
        prefix = f"{self._current_function}."
        matches = [
            symbol
            for symbol in self.symbols.all_symbols()
            if symbol.id == name and symbol.unique_name.startswith(prefix) and symbol.is_captured_ref
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
            if symbol.dict_info.key_type != BaseType.UNKNOWN or symbol.dict_info.value_type != BaseType.UNKNOWN:
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
            if self._expr_is_string_literal(value_ctx) or self._looks_like_rust_string_literal(value):
                return f"String::from({value})"
            return value
        if target_type == BaseType.FLOAT and value_ctx is not None:
            if self._get_expr_type(value_ctx) == BaseType.INTEGER:
                return f"({value} as f64)"
        return value

    def _coerce_to_value_spec(self, value: str, spec: ValueTypeSpec | None, value_ctx=None) -> str:
        """Convert a rendered value to one resolved Zinc payload type when needed."""
        if spec is None:
            return value
        return self._coerce_owned(value, spec.base_type, value_ctx)

    def _nearest_result_error_spec(self, ctx) -> ValueTypeSpec | None:
        """Resolve the active Result error payload for one fail statement."""
        current = ctx.parentCtx
        while current is not None:
            if isinstance(current, ZincParser.TryExpressionContext):
                try_symbol = self._get_expr_symbol(current)
                if try_symbol and try_symbol.result_info:
                    return try_symbol.result_info.err_type
            current = current.parentCtx
        func = self.atlas.functions.get(self._current_function) if self._current_function else None
        if func and func.return_result_info:
            return func.return_result_info.err_type
        return None

    def _borrow_lookup_key(self, value: str, key_type: BaseType, value_ctx=None) -> str:
        """Render a borrowed lookup key for map/set lookup-style methods."""
        if key_type == BaseType.STRING:
            if self._expr_is_string_literal(value_ctx) or self._looks_like_rust_string_literal(value):
                return value
            return f"{value}.as_ref()"
        return f"&{value}"

    def _integer_literal_value(self, ctx) -> int | None:
        """Return an integer literal value for tuple indexes, if statically known."""
        if isinstance(ctx, ZincParser.PrimaryExprContext):
            primary = ctx.primaryExpression()
            if primary and primary.literal() and primary.literal().INTEGER():
                return int(numeric_literal_value(primary.literal().getText()))
        return None

    def _binding_names(self, ctx) -> list[str]:
        """Return identifier names from a binding/destructuring context."""
        return [token.getText() for token in ctx.getTokens(ZincParser.IDENTIFIER)]

    def _typed_assignment_tokens(self, target_ctx) -> list:
        """Return identifier tokens from a typed local binding target."""
        if target_ctx.IDENTIFIER():
            return [target_ctx.IDENTIFIER()]
        if target_ctx.tupleAssignmentTarget():
            return list(target_ctx.tupleAssignmentTarget().getTokens(ZincParser.IDENTIFIER))
        return []

    def _symbol_for_binding_token(self, token):
        """Return the resolved binding symbol for a target token, falling back to the local name."""
        symbol = self.symbols.lookup_by_interval(token.getSourceInterval(), self._current_function)
        if symbol is None or symbol.id is None:
            fallback = self._lookup_local_symbol(token.getText())
            if fallback is not None:
                return fallback
        return symbol

    def _function_call_name(self, expr_ctx) -> str | None:
        """Return the simple callee name for calls like close(...)."""
        if isinstance(expr_ctx, ZincParser.FunctionCallExprContext):
            callee = expr_ctx.expression()
            if isinstance(callee, ZincParser.PrimaryExprContext):
                primary = callee.primaryExpression()
                if primary and primary.IDENTIFIER():
                    return primary.IDENTIFIER().getText()
        return None

    def _render_tuple_pattern(self, names: list[str]) -> str:
        """Render a Rust tuple pattern."""
        if len(names) == 1:
            return f"({names[0]},)"
        return f"({', '.join(names)})"

    def _render_identifier_assignment(self, name: str, symbol, value: str, *, include_type: bool = False) -> str:
        """Render a local binding declaration or reassignment for one identifier."""
        if symbol is None:
            self._declared_vars.add(name)
            return f"let {name} = {value};"

        captured_target = self._symbol_is_captured_cell(symbol)
        storage_name = self._symbol_storage_unique_name(symbol) if captured_target else None
        rendered_target = self._rust_binding_name(storage_name) if storage_name is not None else name
        if captured_target and (symbol.is_captured_ref or not (symbol.is_shadow or name not in self._declared_vars)):
            return f"*{rendered_target}.lock().unwrap() = {value};"

        if symbol.is_shadow or name not in self._declared_vars:
            self._declared_vars.add(name)
            needs_mut = symbol.is_mutated or name in self._mut_struct_vars
            mut_prefix = "mut " if needs_mut else ""
            if storage_name in self._captured_binding_names:
                value = f"Arc::new(Mutex::new({value}))"
            if include_type:
                return f"let {mut_prefix}{rendered_target}: {self._symbol_rust_type(symbol)} = {value};"
            return f"let {mut_prefix}{rendered_target} = {value};"

        return f"{rendered_target} = {value};"

    def _render_broadcast_assignment(self, ctx, target_tuple_ctx, expr_ctx, value: str, *, include_type: bool = False) -> str:
        """Render x, y, z = expr by evaluating expr once and assigning clones in order."""
        tokens = list(target_tuple_ctx.getTokens(ZincParser.IDENTIFIER))
        temp_name = self._staged_temp_name("multi_assign", ctx)
        lines = [f"let {temp_name} = {value};"]
        for i, token in enumerate(tokens):
            name = token.getText()
            symbol = self._symbol_for_binding_token(token)
            item_value = temp_name if i == len(tokens) - 1 else f"{temp_name}.clone()"
            if symbol is not None:
                item_value = self._coerce_numeric_rhs_for_target(item_value, expr_ctx, symbol.resolved_type, symbol.exact_type)
            lines.append(self._render_identifier_assignment(name, symbol, item_value, include_type=include_type))
        return "\n".join(lines)

    def visitUnaryExpr(self, ctx: ZincParser.UnaryExprContext) -> str:
        """Visit unary expression."""
        op = ctx.getChild(0).getText()
        if op == "not":
            op = "!"
        operand = self.visit(ctx.expression())
        return f"({op}{operand})"

    def visitRelationalExpr(self, ctx: ZincParser.RelationalExprContext) -> str:
        """Visit relational comparison."""
        left = self.visit(ctx.expression(0))
        op = ctx.getChild(1).getText()
        right = self.visit(ctx.expression(1))
        left, right = self._promote_numeric_operands(
            left,
            ctx.expression(0),
            right,
            ctx.expression(1),
        )

        return f"({left} {op} {right})"

    def visitEqualityExpr(self, ctx: ZincParser.EqualityExprContext) -> str:
        """Visit equality comparison."""
        left = self.visit(ctx.expression(0))
        op = ctx.getChild(1).getText()
        right = self.visit(ctx.expression(1))
        left, right = self._promote_numeric_operands(
            left,
            ctx.expression(0),
            right,
            ctx.expression(1),
        )

        return f"({left} {op} {right})"

    def visitMembershipExpr(self, ctx: ZincParser.MembershipExprContext) -> str:
        """Visit membership comparison."""
        left = self.visit(ctx.expression(0))
        right = self.visit(ctx.expression(1))
        right_type = self._get_expr_type(ctx.expression(1))
        if right_type == BaseType.SET:
            return f"({right}.contains(&{left}))"
        if right_type == BaseType.DICT:
            return f"({right}.contains_key(&{left}))"
        return f"({right}.contains(&{left}))"

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
                key = self._visit_expression_with_expectations(
                    key_ctx,
                    expected_type=info.key_type,
                    callable_info=info.key_callable_info,
                    coerce_scalar=False,
                    coerce_callable=False,
                )
                value = self._visit_expression_with_expectations(
                    value_ctx,
                    expected_type=info.value_type,
                    callable_info=info.value_callable_info,
                    coerce_scalar=False,
                    coerce_callable=False,
                )
                key = self._coerce_owned(key, info.key_type, key_ctx)
                value = self._coerce_owned(value, info.value_type, value_ctx)
                entries.append(f"({key}, {value})")
            return f"{info.rust_container()}::from([{', '.join(entries)}])"

        info = self._expected_set_info or self._get_set_info(ctx) or SetTypeInfo()
        elements = []
        for expr_ctx in ctx.expression():
            elem = self._visit_expression_with_expectations(
                expr_ctx,
                expected_type=info.element_type,
                coerce_scalar=False,
                coerce_callable=False,
            )
            elem = self._coerce_owned(elem, info.element_type, expr_ctx)
            elements.append(elem)
        return f"{info.rust_container()}::from([{', '.join(elements)}])"

    def visitIndexAccessExpr(self, ctx: ZincParser.IndexAccessExprContext) -> str:
        """Visit index access."""
        constant_value = self._constant_value_for_expr(ctx)
        if constant_value is not None:
            return self._render_constant_value(constant_value)
        collection_type = self._get_expr_type(ctx.expression(0))
        receiver_symbol = self._get_expr_symbol(ctx.expression(0))
        captured_collection_name = None
        if receiver_symbol and self._symbol_is_captured_cell(receiver_symbol):
            storage_name = self._symbol_storage_unique_name(receiver_symbol)
            if storage_name is not None:
                captured_collection_name = self._rust_binding_name(storage_name)
        collection = self.visit(ctx.expression(0))
        index = self.visit(ctx.expression(1))
        if collection_type == BaseType.DICT:
            info = self._get_dict_info(ctx.expression(0)) or DictTypeInfo()
            key = self._borrow_lookup_key(index, info.key_type, ctx.expression(1))
            if captured_collection_name is not None:
                return f"{captured_collection_name}.lock().unwrap().get({key}).unwrap().clone()"
            return f"{collection}.get({key}).unwrap().clone()"
        if collection_type == BaseType.TUPLE:
            tuple_index = self._integer_literal_value(ctx.expression(1))
            if tuple_index is not None:
                value = f"{collection}.{tuple_index}"
                result_type = self._get_expr_type(ctx)
                if result_type == BaseType.ENUM:
                    return f"{value}.clone()"
                return value

        index_ctx = ctx.expression(1)
        # Cast non-literal integer indices to usize (Rust Vec indexing requires usize)
        index_type = self._get_expr_type(index_ctx)
        if index_type == BaseType.INTEGER and not self._is_integer_literal(index_ctx):
            index = f"({index} as usize)"
        if captured_collection_name is not None:
            result_type = self._get_expr_type(ctx)
            if result_type == BaseType.ENUM:
                return f"{captured_collection_name}.lock().unwrap()[{index}].clone()"
            return f"{captured_collection_name}.lock().unwrap()[{index}]"
        result_type = self._get_expr_type(ctx)
        if result_type == BaseType.ENUM:
            return f"{collection}[{index}].clone()"
        return f"{collection}[{index}]"

    def _is_integer_literal(self, ctx) -> bool:
        """Return True if expression is a bare integer literal (e.g. 0, 1, 2)."""
        if isinstance(ctx, ZincParser.PrimaryExprContext):
            primary = ctx.primaryExpression()
            if primary and primary.literal():
                lit_text = primary.literal().getText()
                return bool(lit_text) and primary.literal().INTEGER() is not None
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
        constant_value = self._constant_value_for_expr(ctx)
        if constant_value is not None:
            return self._render_constant_value(constant_value)
        expr_symbol = self._get_expr_symbol(ctx)
        is_direct_call = isinstance(ctx.parentCtx, ZincParser.FunctionCallExprContext) and ctx.parentCtx.expression() is ctx
        if (
            expr_symbol
            and expr_symbol.resolved_type == BaseType.CALLABLE
            and expr_symbol.callable_info
            and not is_direct_call
            and self._is_direct_callable_expr(ctx, expr_symbol)
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
                    owner_symbol, method_name = static_target
                    if owner_symbol.kind == "struct":
                        struct = self.atlas.structs.get(owner_symbol.qualified_name)
                        if struct:
                            return f"{self._struct_rust_name(struct)}::{method_name}"
                    if owner_symbol.kind == "enum":
                        enum = self.atlas.enums.get(owner_symbol.qualified_name)
                        if enum:
                            return f"{self._enum_rust_name(enum)}::{method_name}"
                    return f"{self.module_graph.rust_base_name(owner_symbol.qualified_name)}::{method_name}"

                enum_variant = self.module_graph.resolve_enum_variant_path(self._current_module, path)
                if enum_variant:
                    enum_symbol, variant_name = enum_variant
                    return f"{self._named_enum_rust_name(enum_symbol.qualified_name)}::{variant_name}"

                struct_symbol = self.module_graph.resolve_struct_path(self._current_module, path)
                if struct_symbol:
                    struct = self.atlas.structs.get(struct_symbol.qualified_name)
                    if struct:
                        return self._struct_rust_name(struct)
                    return self.module_graph.rust_base_name(struct_symbol.qualified_name)

                enum_symbol = self.module_graph.resolve_enum_path(self._current_module, path)
                if enum_symbol:
                    enum = self.atlas.enums.get(enum_symbol.qualified_name)
                    if enum:
                        return self._enum_rust_name(enum)
                    return self.module_graph.rust_base_name(enum_symbol.qualified_name)

        if isinstance(ctx.expression(), ZincParser.PrimaryExprContext):
            primary = ctx.expression().primaryExpression()
            if primary and primary.IDENTIFIER():
                receiver_name = primary.IDENTIFIER().getText()
                receiver_symbol = self._get_expr_symbol(ctx.expression())
                if receiver_symbol and self._symbol_is_captured_cell(receiver_symbol):
                    storage_name = self._symbol_storage_unique_name(receiver_symbol)
                    if storage_name is not None:
                        field_expr = f"{self._rust_binding_name(storage_name)}.lock().unwrap().{ctx.IDENTIFIER().getText()}"
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
        # Regular member access (field or instance method)
        obj = self.visit(ctx.expression())
        return f"{obj}.{ctx.IDENTIFIER().getText()}"

    def visitFunctionCallExpr(self, ctx: ZincParser.FunctionCallExprContext) -> str:
        """Visit function call, handling static and instance method calls."""
        constant_value = self._constant_value_for_expr(ctx)
        if constant_value is not None:
            return self._render_constant_value(constant_value)
        callee_ctx = ctx.expression()
        call_args = self._call_args_for_ctx(ctx)
        spread_setup, spread_temps = self._prepare_spread_temps(call_args, "arg_spread")
        self._spread_temp_stack.append(spread_temps)

        def finish(value: str) -> str:
            self._spread_temp_stack.pop()
            return self._wrap_spread_temps(value, spread_setup)

        arg_ctxs = [self._call_arg_expr(arg) for arg in call_args]
        args = [self._visit_call_arg(arg) for arg in call_args]

        if self._function_call_name(ctx) == "close":
            channel_arg = args[0] if args else "__zinc_missing_close_arg"
            return finish(f"{channel_arg}.close()")

        path = extract_identifier_path(callee_ctx) if self._current_module is not None else None
        if path == ["Context", "background"]:
            return finish("__ZincContext::background()")
        if path == ["Context", "with_cancel"]:
            parent = args[0] if args else "__zinc_missing_context"
            cancel_info = CallableTypeInfo(param_types=[], return_type=BaseType.VOID)
            expr_symbol = self._get_expr_symbol(ctx)
            if expr_symbol and expr_symbol.tuple_info and 1 in expr_symbol.tuple_info.element_callable_infos:
                cancel_info = expr_symbol.tuple_info.element_callable_infos[1]
            cancel_type = cancel_info.rust_type_name()
            cancel_target = (
                cancel_info.targets[0]
                if cancel_info.targets
                else CallableTarget(
                    kind="context_cancel",
                    qualified_name="__zinc_context_cancel",
                    display_name="cancel",
                )
            )
            cancel_variant = self._callable_variant_name(cancel_info, cancel_target)
            return finish(
                "\n".join(
                    [
                        "{",
                        f"    let __zinc_parent_ctx = {parent}.clone();",
                        "    let __zinc_child_ctx = __ZincContext::background();",
                        "    let __zinc_child_for_task = __zinc_child_ctx.clone();",
                        "    tokio::spawn(async move {",
                        "        let _ = __zinc_parent_ctx.done().recv_option().await;",
                        "        __zinc_child_for_task.cancel();",
                        "    });",
                        f"    (__zinc_child_ctx.clone(), {cancel_type}::{cancel_variant}(__zinc_child_ctx))",
                        "}",
                    ]
                )
            )

        # Get callee text first to check for static method
        callee = self.visit(callee_ctx)
        callee_symbol = self._get_expr_symbol(callee_ctx)
        direct_key = (self._current_function, ctx.getSourceInterval())
        direct_mangled = self._specialization_map.get(direct_key)
        if direct_mangled:
            func = self.atlas.functions.get(direct_mangled)
            if func is not None:
                args = self._render_function_args_for_instance(func, call_args)
            else:
                args = [self._visit_call_arg(arg) for arg in call_args]
            args = self._process_function_args(direct_mangled, args, arg_ctxs)
            if func is not None:
                closure_info = self._closure_info(func.qualified_name)
                if closure_info is not None:
                    args = [self._closure_env_constructor(closure_info), *args]
            call = f"{direct_mangled}({', '.join(args)})"
            if func and func.is_async:
                return finish(f"{call}.await")
            return finish(call)

        if isinstance(callee_ctx, ZincParser.MemberAccessExprContext):
            receiver_ctx = callee_ctx.expression()
            method_name = callee_ctx.IDENTIFIER().getText()
            if self._get_expr_type(receiver_ctx) == BaseType.CONTEXT:
                if method_name == "done":
                    return finish(f"{self.visit(receiver_ctx)}.done()")
                if method_name == "cancel":
                    return finish(f"{self.visit(receiver_ctx)}.cancel()")

        if callee == "print":
            return finish(self._render_print_call(args, arg_ctxs))

        if callee in {"dict", "sort_dict"}:
            info = self._expected_dict_info or self._get_dict_info(ctx) or DictTypeInfo(kind=callee)
            collection_type = info.rust_container()
            if info.key_type != BaseType.UNKNOWN and info.value_type != BaseType.UNKNOWN:
                key = self._type_with_metadata_to_rust(
                    info.key_type,
                    callable_info=info.key_callable_info,
                    struct_qualified_name=info.key_struct_qualified_name,
                    anonymous_struct_info=info.key_anonymous_struct_info,
                    as_reference=False,
                )
                value = self._type_with_metadata_to_rust(
                    info.value_type,
                    callable_info=info.value_callable_info,
                    struct_qualified_name=info.value_struct_qualified_name,
                    anonymous_struct_info=info.value_anonymous_struct_info,
                    as_reference=False,
                )
                return finish(f"{collection_type}::<{key}, {value}>::new()")
            return finish(f"{collection_type}::new()")

        if callee in {"set", "sort_set"}:
            info = self._expected_set_info or self._get_set_info(ctx) or SetTypeInfo(kind=callee)
            collection_type = info.rust_container()
            if info.element_type != BaseType.UNKNOWN:
                elem = self._type_with_metadata_to_rust(
                    info.element_type,
                    struct_qualified_name=info.element_struct_qualified_name,
                    anonymous_struct_info=info.element_anonymous_struct_info,
                    as_reference=False,
                )
                return finish(f"{collection_type}::<{elem}>::new()")
            return finish(f"{collection_type}::new()")

        # Static method call (StructName::method)
        if "::" in callee:
            struct_name, method_name = callee.rsplit("::", 1)
            struct = next((s for s in self.atlas.structs.values() if self._struct_rust_name(s) == struct_name), None)
            if struct:
                args = self._process_method_args(struct, method_name, args, arg_ctxs)
            return finish(f"{callee}({', '.join(args)})")

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
                args = self._render_callable_args_for_signature(callee_symbol.callable_info, call_args)
                args = self._process_callable_args(callee_symbol.callable_info, args, arg_ctxs)
                callable_expr = callee
                if isinstance(callee_ctx, ZincParser.MemberAccessExprContext):
                    callable_expr = self._render_callable_value(callee_symbol.callable_info)
                return finish(f"{callable_expr}.call({', '.join(args)})")

        if self._current_module is not None:
            path = extract_identifier_path(callee_ctx)
            if path:
                resolved_function = self.module_graph.resolve_function_path(self._current_module, path)
                if resolved_function:
                    key = (self._current_function, ctx.getSourceInterval())
                    mangled = self._specialization_map.get(key) or self.module_graph.rust_base_name(resolved_function.qualified_name)
                    func = self.atlas.functions.get(mangled)
                    if func is not None:
                        args = self._render_function_args_for_instance(func, call_args)
                    else:
                        args = [self._visit_call_arg(arg) for arg in call_args]
                    args = self._process_function_args(mangled, args, arg_ctxs)
                    call = f"{mangled}({', '.join(args)})"
                    if self.atlas.functions.get(mangled) and self.atlas.functions[mangled].is_async:
                        return finish(f"{call}.await")
                    return finish(call)

        # Instance method call (obj.method) - already visited, callee is "obj.method"
        if isinstance(callee_ctx, ZincParser.MemberAccessExprContext):
            # Check if this is an instance method on a struct variable
            target_ctx = callee_ctx.expression()
            method_name = callee_ctx.IDENTIFIER().getText()
            receiver_type = self._get_expr_type(target_ctx)
            receiver_symbol = self._get_expr_symbol(target_ctx)
            captured_receiver_name = None
            if receiver_symbol and self._symbol_is_captured_cell(receiver_symbol):
                storage_name = self._symbol_storage_unique_name(receiver_symbol)
                if storage_name is not None:
                    captured_receiver_name = self._rust_binding_name(storage_name)
            if receiver_type == BaseType.DICT:
                target = self.visit(target_ctx)
                dict_target = f"{captured_receiver_name}.lock().unwrap()" if captured_receiver_name else target
                info = self._get_dict_info(target_ctx) or DictTypeInfo()
                if method_name == "len":
                    return finish(f"({dict_target}.len() as i64)")
                if method_name == "is_empty":
                    return finish(f"{dict_target}.is_empty()")
                if method_name == "clear":
                    return finish(f"{{ {dict_target}.clear(); () }}")
                if method_name == "keys":
                    return finish(f"{dict_target}.keys().cloned().collect::<Vec<_>>()")
                if method_name == "values":
                    return finish(f"{dict_target}.values().cloned().collect::<Vec<_>>()")
                if method_name == "items":
                    return finish(f"{dict_target}.iter().map(|(k, v)| (k.clone(), v.clone())).collect::<Vec<_>>()")
                if method_name == "insert" and len(args) == 2:
                    key = self._coerce_owned(args[0], info.key_type, arg_ctxs[0] if arg_ctxs else None)
                    value = self._coerce_owned(args[1], info.value_type, arg_ctxs[1] if arg_ctxs else None)
                    return finish(f"{{ {dict_target}.insert({key}, {value}); () }}")
                if method_name in {"get", "contains_key", "remove"} and len(args) == 1:
                    key = self._borrow_lookup_key(args[0], info.key_type, arg_ctxs[0] if arg_ctxs else None)
                    if method_name == "get":
                        return finish(f"{dict_target}.get({key}).unwrap().clone()")
                    if method_name == "remove":
                        return finish(f"{{ {dict_target}.remove({key}); () }}")
                    return finish(f"{dict_target}.{method_name}({key})")

            if receiver_type == BaseType.SET:
                target = self.visit(target_ctx)
                set_target = f"{captured_receiver_name}.lock().unwrap()" if captured_receiver_name else target
                info = self._get_set_info(target_ctx) or SetTypeInfo()
                if method_name == "len":
                    return finish(f"({set_target}.len() as i64)")
                if method_name == "is_empty":
                    return finish(f"{set_target}.is_empty()")
                if method_name == "clear":
                    return finish(f"{{ {set_target}.clear(); () }}")
                if method_name in {"push", "insert"} and len(args) == 1:
                    elem = self._coerce_owned(args[0], info.element_type, arg_ctxs[0] if arg_ctxs else None)
                    return finish(f"{{ {set_target}.insert({elem}); () }}")
                if method_name in {"contains", "remove"} and len(args) == 1:
                    elem = self._borrow_lookup_key(args[0], info.element_type, arg_ctxs[0] if arg_ctxs else None)
                    if method_name == "remove":
                        return finish(f"{{ {set_target}.remove({elem}); () }}")
                    return finish(f"{set_target}.{method_name}({elem})")

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
                    and self._is_direct_callable_expr(arg_ctx, arg_symbol)
                ):
                    args[0] = self._render_callable_value_for_signature(
                        arg_symbol.callable_info,
                        receiver_symbol.callable_info,
                    )
                if captured_receiver_name is not None:
                    return finish(f"{captured_receiver_name}.lock().unwrap().push({args[0]})")

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
                            if captured_receiver_name is not None and method:
                                result = f"{captured_receiver_name}.lock().unwrap().{method_name}({', '.join(args)})"
                                if method_name == "len":
                                    return finish(f"({result} as i64)")
                                return finish(result)
                            if self._boxed_struct_key(target_var) in self._boxed_struct_vars and method:
                                borrow = "borrow_mut" if method.self_mutability == "&mut self" else "borrow"
                                result = f"{target_var}.{borrow}().{method_name}({', '.join(args)})"
                                if method_name == "len":
                                    return finish(f"({result} as i64)")
                                return finish(result)
            result = f"{callee}({', '.join(args)})"
            # len() returns usize in Rust but Zinc treats all integers as i64
            if method_name == "len":
                return finish(f"({result} as i64)")
            return finish(result)

        # Look up mangled name from specialization map (scoped by current function)
        key = (self._current_function, ctx.getSourceInterval())
        mangled = self._specialization_map.get(key)
        if mangled:
            # Process arguments for string literal conversion
            args = self._process_function_args(mangled, args, arg_ctxs)
            func = self.atlas.functions.get(mangled)
            if func is not None:
                closure_info = self._closure_info(func.qualified_name)
                if closure_info is not None:
                    args = [self._closure_env_constructor(closure_info), *args]
            call = f"{mangled}({', '.join(args)})"
            if func and func.is_async:
                return finish(f"{call}.await")
            return finish(call)

        return finish(f"{callee}({', '.join(args)})")

    def _render_function_args_for_instance(self, func: FunctionInstance, call_args: list) -> list[str]:
        """Render function-call arguments with the function signature as context."""
        rendered: list[str] = []
        for i, arg in enumerate(call_args):
            rendered.append(
                self._visit_call_arg_with_expectations(
                    arg,
                    expected_type=func.arg_types[i] if i < len(func.arg_types) else None,
                    dict_info=func.arg_dict_infos.get(i),
                    set_info=func.arg_set_infos.get(i),
                    tuple_info=func.arg_tuple_infos.get(i),
                    callable_info=func.arg_callable_infos.get(i),
                    coerce_scalar=False,
                    coerce_callable=False,
                )
            )
        return rendered

    def _render_callable_args_for_signature(self, callable_info: CallableTypeInfo, call_args: list) -> list[str]:
        """Render indirect-call arguments with a callable signature as context."""
        rendered: list[str] = []
        for i, arg in enumerate(call_args):
            rendered.append(
                self._visit_call_arg_with_expectations(
                    arg,
                    expected_type=callable_info.param_types[i] if i < len(callable_info.param_types) else None,
                    dict_info=callable_info.param_dict_infos.get(i),
                    set_info=callable_info.param_set_infos.get(i),
                    tuple_info=callable_info.param_tuple_infos.get(i),
                    callable_info=callable_info.param_callable_infos.get(i),
                    coerce_scalar=False,
                    coerce_callable=False,
                )
            )
        return rendered

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
                arg_ctx = arg_ctxs[i] if arg_ctxs and i < len(arg_ctxs) else None

                # Convert string literal to String::from() for String parameters
                if param_type == BaseType.STRING and (self._expr_is_string_literal(arg_ctx) or self._looks_like_rust_string_literal(arg)):
                    processed.append(f"String::from({arg})")
                elif param_type == BaseType.CHANNEL and i in func.arg_channel_infos:
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
                    arg_symbol = self._get_expr_symbol(arg_ctx) if arg_ctx is not None else None
                    if arg_symbol and arg_symbol.callable_info and self._is_direct_callable_expr(arg_ctx, arg_symbol):
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
                arg_ctx = arg_ctxs[i] if arg_ctxs and i < len(arg_ctxs) else None

                # Convert string literal to String::from() for String parameters
                if (
                    param_type
                    and param_type.lower() == "string"
                    and (self._expr_is_string_literal(arg_ctx) or self._looks_like_rust_string_literal(arg))
                ):
                    processed.append(f"String::from({arg})")
                # Apply integer narrowing for literals
                elif param_type and param_type in ("i32", "i64"):
                    narrowed = self._apply_literal_narrowing(arg, param_type, arg_ctx)
                    processed.append(narrowed)
                else:
                    processed.append(arg)
            else:
                processed.append(arg)

        return processed

    def _apply_literal_narrowing(self, arg: str, target_type: str, arg_ctx=None) -> str:
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
                    if lit_text and is_numeric_literal(lit_text):
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
                return bool(lit_text) and is_numeric_literal(lit_text)
        return False

    def _render_print_call(self, args: list[str], arg_ctxs: list | None = None) -> str:
        """Render a print() call as println!()."""
        if not args:
            return "println!()"
        arg = args[0]
        arg_ctx = arg_ctxs[0] if arg_ctxs else None
        arg_symbol = self._get_expr_symbol(arg_ctx) if arg_ctx is not None else None
        if arg_symbol and isinstance(arg_symbol.constant_value, (MetaValue, MetaListValue)):
            return f'println!("{{:?}}", {arg})'
        if arg.startswith("format!("):
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
        return f'println!("{{}}", {arg})'

    def visitChannelReceiveExpr(self, ctx: ZincParser.ChannelReceiveExprContext) -> str:
        """Visit channel receive expression."""
        chan_expr = ctx.expression()
        receiver = self.visit(chan_expr)
        return f"{receiver}.recv().await"

    def visitStructInstantiation(self, ctx: ZincParser.StructInstantiationContext) -> str:
        """Visit struct instantiation."""
        expr_symbol = self._get_expr_symbol(ctx)
        concrete_anonymous_struct = expr_symbol.anonymous_struct_info if expr_symbol else None
        if self._current_module is None:
            name = concrete_anonymous_struct.rust_type_name() if concrete_anonymous_struct else ctx.qualifiedName().getText()
            struct = None
        else:
            struct_symbol = self.module_graph.resolve_struct_path(self._current_module, struct_path_from_ctx(ctx))
            if (
                struct_symbol is not None
                and self._current_struct is not None
                and self._current_constructor_owner is not None
                and struct_symbol.qualified_name == self._current_constructor_owner
            ):
                struct = self.atlas.structs.get(self._current_struct)
                if concrete_anonymous_struct is not None:
                    name = concrete_anonymous_struct.rust_type_name()
                else:
                    name = self._struct_rust_name(struct) if struct else ctx.qualifiedName().getText()
            else:
                struct = self.atlas.structs.get(struct_symbol.qualified_name) if struct_symbol else None
                if concrete_anonymous_struct is not None:
                    name = concrete_anonymous_struct.rust_type_name()
                else:
                    name = self._struct_rust_name(struct) if struct else ctx.qualifiedName().getText()

        bound_fields = self._struct_fields_for_ctx(ctx)
        if not bound_fields:
            raw_fields, has_spread = self._raw_struct_literal_fields(ctx)
            if has_spread:
                raise RuntimeError("internal error: struct spread was not bound during semantic analysis")
            if struct:
                fields = []
                for f in struct.fields:
                    if f.name in raw_fields:
                        value, expr_ctx = raw_fields[f.name]
                        if f.rust_type() == "String" and (
                            self._expr_is_string_literal(expr_ctx) or self._looks_like_rust_string_literal(value)
                        ):
                            value = f"String::from({value})"
                        fields.append(f"{f.name}: {value}")
                    else:
                        fields.append(f"{f.name}: {f.rust_default()}")
                return f"{name} {{ {', '.join(fields)} }}"
            return f"{name} {{ {', '.join(f'{field_name}: {value}' for field_name, (value, _expr) in raw_fields.items())} }}"

        spread_setup, spread_temps = self._prepare_spread_temps(bound_fields, "field_spread")
        self._spread_temp_stack.append(spread_temps)
        provided_fields = {field.name: field for field in bound_fields}

        # Look up struct definition to get all fields with defaults
        if struct:
            concrete_field_map = concrete_anonymous_struct.field_map() if concrete_anonymous_struct else {}
            fields = []
            for f in struct.fields:
                if f.name in provided_fields:
                    bound_field = provided_fields[f.name]
                    value = self._render_bound_struct_field(bound_field, expected_type=f.resolved_type)
                    concrete_field = concrete_field_map.get(f.name)
                    rust_type = (
                        self._type_with_metadata_to_rust(
                            concrete_field.resolved_type,
                            exact_type=concrete_field.exact_type,
                            array_info=concrete_field.array_info,
                            dict_info=concrete_field.dict_info,
                            set_info=concrete_field.set_info,
                            tuple_info=concrete_field.tuple_info,
                            callable_info=concrete_field.callable_info,
                            struct_qualified_name=concrete_field.struct_qualified_name,
                            anonymous_struct_info=concrete_field.anonymous_struct_info,
                            as_reference=False,
                        )
                        if concrete_field is not None
                        else f.rust_type()
                    )
                    # Convert string literals to String::from() for String fields
                    if rust_type == "String" and (
                        bound_field.spread_source_expr is None
                        and (self._expr_is_string_literal(bound_field.expression) or self._looks_like_rust_string_literal(value))
                    ):
                        value = f"String::from({value})"
                    fields.append(f"{f.name}: {value}")
                else:
                    # Use default value
                    fields.append(f"{f.name}: {f.rust_default()}")
            fields_str = ", ".join(fields)
            self._spread_temp_stack.pop()
            return self._wrap_spread_temps(f"{name} {{ {fields_str} }}", spread_setup)
        # Fallback - just use provided fields
        fields = [f"{field.name}: {self._render_bound_struct_field(field)}" for field in bound_fields]
        fields_str = ", ".join(fields)
        self._spread_temp_stack.pop()
        return self._wrap_spread_temps(f"{name} {{ {fields_str} }}", spread_setup)

    def visitEnumVariantConstruction(self, ctx: ZincParser.EnumVariantConstructionContext) -> str:
        """Visit enum payload construction."""
        variant_name = ctx.enumVariantPath().IDENTIFIER().getText()
        owner_rust = ctx.enumVariantPath().qualifiedName().getText()
        variant = None
        if self._current_module is not None:
            target = self.module_graph.resolve_enum_variant_path(
                self._current_module,
                ctx.enumVariantPath().getText().split("."),
            )
            if target is not None:
                enum_symbol, variant_name = target
                owner_rust = self._named_enum_rust_name(enum_symbol.qualified_name)
                enum_info = self.atlas.enums.get(enum_symbol.qualified_name)
                if enum_info is not None:
                    variant = next(
                        (candidate for candidate in enum_info.variants if candidate.name == variant_name),
                        None,
                    )
            else:
                struct_symbol = self.module_graph.resolve_struct_path(
                    self._current_module,
                    ctx.enumVariantPath().getText().split("."),
                )
                if struct_symbol is not None:
                    struct = self.atlas.structs.get(struct_symbol.qualified_name)
                    name = self._struct_rust_name(struct) if struct else ctx.enumVariantPath().getText()
                    provided_fields = {field.IDENTIFIER().getText(): self.visit(field.expression()) for field in ctx.fieldInit()}
                    provided_field_exprs = {field.IDENTIFIER().getText(): field.expression() for field in ctx.fieldInit()}
                    if struct is not None:
                        fields = []
                        for info in struct.fields:
                            if info.name in provided_fields:
                                value = provided_fields[info.name]
                                if info.rust_type() == "String" and (
                                    self._expr_is_string_literal(provided_field_exprs.get(info.name))
                                    or self._looks_like_rust_string_literal(value)
                                ):
                                    value = f"String::from({value})"
                                fields.append(f"{info.name}: {value}")
                            else:
                                fields.append(f"{info.name}: {info.rust_default()}")
                        return f"{name} {{ {', '.join(fields)} }}"
                    return f"{name} {{ {', '.join(f'{key}: {value}' for key, value in provided_fields.items())} }}"

        provided = {field.IDENTIFIER().getText(): (self.visit(field.expression()), field.expression()) for field in ctx.fieldInit()}
        if variant is not None:
            field_parts = []
            for field in variant.fields:
                value, expr_ctx = provided[field.name]
                field_parts.append(f"{field.name}: {self._coerce_owned(value, field.resolved_type, expr_ctx)}")
        else:
            field_parts = [f"{name}: {value}" for name, (value, _expr) in provided.items()]
        return f"{owner_rust}::{variant_name} {{ {', '.join(field_parts)} }}"

    def _match_pattern_local_names(self, pattern_ctx) -> set[str]:
        """Return the names introduced by one match pattern."""
        result_option_pattern = pattern_ctx.resultOptionPattern()
        if result_option_pattern is not None and result_option_pattern.pattern() is not None:
            return self._match_pattern_local_names(result_option_pattern.pattern())
        if pattern_ctx.IDENTIFIER():
            return {pattern_ctx.IDENTIFIER().getText()}
        enum_pattern = pattern_ctx.enumVariantPattern()
        if enum_pattern is None:
            return set()
        names = set()
        for field_pattern in enum_pattern.enumVariantFieldPattern():
            identifiers = list(field_pattern.IDENTIFIER())
            if identifiers:
                names.add(identifiers[-1].getText())
        return names

    def _render_match_pattern(self, pattern_ctx) -> str:
        """Render one match arm pattern to Rust."""
        if pattern_ctx.getText() == "_":
            return "_"
        result_option_pattern = pattern_ctx.resultOptionPattern()
        if result_option_pattern is not None:
            if result_option_pattern.NONE():
                return "None"
            inner = self._render_match_pattern(result_option_pattern.pattern())
            if result_option_pattern.OK():
                return f"Ok({inner})"
            if result_option_pattern.ERR():
                return f"Err({inner})"
            return f"Some({inner})"
        if pattern_ctx.IDENTIFIER():
            return pattern_ctx.IDENTIFIER().getText()
        enum_pattern = pattern_ctx.enumVariantPattern()
        if enum_pattern is None or self._current_module is None:
            return pattern_ctx.getText()
        target = self.module_graph.resolve_enum_variant_path(
            self._current_module,
            enum_pattern.enumVariantPath().getText().split("."),
        )
        if target is None:
            return pattern_ctx.getText().replace(".", "::")
        enum_symbol, variant_name = target
        owner_rust = self._named_enum_rust_name(enum_symbol.qualified_name)
        field_patterns = list(enum_pattern.enumVariantFieldPattern())
        if not field_patterns:
            return f"{owner_rust}::{variant_name}"
        fields = []
        for field_pattern in field_patterns:
            identifiers = list(field_pattern.IDENTIFIER())
            if len(identifiers) == 1:
                fields.append(identifiers[0].getText())
            else:
                fields.append(f"{identifiers[0].getText()}: {identifiers[1].getText()}")
        return f"{owner_rust}::{variant_name} {{ {', '.join(fields)} }}"

    def _render_match_arm_body(self, arm_ctx, local_names: set[str]) -> list[str]:
        """Render one match arm body with its pattern bindings in scope."""
        previous_declared = set(self._declared_vars)
        self._declared_vars.update(local_names)
        try:
            if arm_ctx.block() is not None:
                return self._generate_block(arm_ctx.block())
            rendered = self.visit(arm_ctx.expression())
            return [rendered if rendered.endswith(";") else f"{rendered};"]
        finally:
            self._declared_vars = previous_declared

    # --- Statement Visitors (return Rust statement strings) ---

    def visitMatchStatement(self, ctx: ZincParser.MatchStatementContext) -> str:
        """Visit a statement-form match."""
        scrutinee = self.visit(ctx.expression())
        staged_name = self._staged_temp_name("match", ctx)
        lines = [
            "{",
            f"    let {staged_name} = {scrutinee};",
            f"    match {staged_name}.clone() {{",
        ]
        for arm_ctx in ctx.matchArm():
            pattern = self._render_match_pattern(arm_ctx.pattern())
            body = self._render_match_arm_body(
                arm_ctx,
                self._match_pattern_local_names(arm_ctx.pattern()),
            )
            lines.append(f"        {pattern} => {{")
            self._append_block_lines(lines, body, 3)
            lines.append("        },")
        lines.append("    }")
        lines.append("}")
        return "\n".join(lines)

    def visitFunctionDeclaration(self, ctx: ZincParser.FunctionDeclarationContext) -> str | None:
        """Nested functions are generated separately as hidden top-level Rust functions."""
        return None

    def visitAsyncFunctionDeclaration(self, ctx: ZincParser.AsyncFunctionDeclarationContext) -> str | None:
        """Nested async functions are generated separately as hidden top-level Rust functions."""
        return None

    def visitBlockExpr(self, ctx: ZincParser.BlockExprContext) -> str:
        """Visit a block-expression wrapper."""
        return self.visit(ctx.blockExpression())

    def visitBlockExpression(self, ctx: ZincParser.BlockExpressionContext) -> str:
        """Render a plain block expression."""
        return self._render_value_block_expr(ctx)

    def _render_try_tail(self, stmt_ctx, family: BaseType) -> list[str]:
        """Render the final statement of a try block, wrapping successful values."""
        if stmt_ctx.expressionStatement():
            value = self._render_expression_value(stmt_ctx.expressionStatement().expression())
            wrapper = "Ok" if family == BaseType.RESULT else "Some"
            return [f"{wrapper}({value})"]
        if stmt_ctx.block():
            value = self._render_value_block_expr(stmt_ctx.block())
            wrapper = "Ok" if family == BaseType.RESULT else "Some"
            return [f"{wrapper}({value})"]
        if stmt_ctx.ifStatement():
            value = self._render_if_statement(stmt_ctx.ifStatement(), as_expression=True)
            wrapper = "Ok" if family == BaseType.RESULT else "Some"
            return [f"{wrapper}({value})"]
        if stmt_ctx.returnStatement():
            return [self.visit(stmt_ctx.returnStatement())]
        if stmt_ctx.failStatement():
            return [self.visit(stmt_ctx.failStatement())]
        if stmt_ctx.breakStatement():
            return [self.visit(stmt_ctx.breakStatement())]
        if stmt_ctx.continueStatement():
            return [self.visit(stmt_ctx.continueStatement())]
        rendered = self.visit(stmt_ctx)
        if not rendered:
            return ["Ok(())" if family == BaseType.RESULT else "Some(())"]
        return [rendered, "Ok(())" if family == BaseType.RESULT else "Some(())"]

    def _render_try_block(self, block_ctx, family: BaseType) -> list[str]:
        """Render the body of a try closure."""
        previous_declared = set(self._declared_vars)
        try:
            statements = list(block_ctx.statement())
            if not statements:
                return ["Ok(())" if family == BaseType.RESULT else "Some(())"]
            stmts: list[str] = []
            for stmt_ctx in statements[:-1]:
                self._append_rendered_statement(stmts, self.visit(stmt_ctx))
            stmts.extend(self._render_try_tail(statements[-1], family))
            return stmts
        finally:
            self._declared_vars = previous_declared

    def visitTryExpr(self, ctx: ZincParser.TryExprContext) -> str:
        """Visit a try-expression wrapper."""
        return self.visit(ctx.tryExpression())

    def visitTryExpression(self, ctx: ZincParser.TryExpressionContext) -> str:
        """Render a try block as an immediately-invoked closure."""
        expr_symbol = self._get_expr_symbol(ctx)
        family = expr_symbol.resolved_type if expr_symbol else self._get_expr_type(ctx)
        if family == BaseType.RESULT and expr_symbol and expr_symbol.result_info:
            return_type = expr_symbol.result_info.to_rust_type()
        elif family == BaseType.OPTION and expr_symbol and expr_symbol.option_info:
            return_type = expr_symbol.option_info.to_rust_type()
        else:
            return_type = exact_type_to_rust(expr_symbol.exact_type if expr_symbol else None, family)
        lines = [f"(|| -> {return_type} {{"]
        self._append_block_lines(lines, self._render_try_block(ctx.block(), family), 1)
        lines.append("})()")
        return "\n".join(lines)

    def visitOutCaptureDeclaration(self, ctx: ZincParser.OutCaptureDeclarationContext) -> str:
        """The `out` marker is semantic-only; assignments perform the writes."""
        return ""

    def visitTypedVariableAssignment(self, ctx: ZincParser.TypedVariableAssignmentContext) -> str:
        """Visit a typed local declaration."""
        target_ctx = ctx.typedAssignmentTarget()
        if target_ctx.tupleAssignmentTarget():
            value = self._visit_expression_with_expectations(ctx.expression(), coerce_scalar=False)
            expr_type = self._get_expr_type(ctx.expression())
            tuple_info = self._get_tuple_info(ctx.expression())
            if expr_type == BaseType.TUPLE and tuple_info is not None:
                tokens = self._typed_assignment_tokens(target_ctx)
                target_symbols = [self._symbol_for_binding_token(token) for token in tokens]
                temp_name = self._staged_temp_name("destructure", ctx)
                lines = [f"let {temp_name} = {value};"]
                for i, (token, symbol) in enumerate(zip(tokens, target_symbols, strict=False)):
                    name = token.getText()
                    item_value = f"{temp_name}.{i}"
                    if (
                        symbol is not None
                        and i < len(tuple_info.element_types)
                        and symbol.resolved_type == BaseType.FLOAT
                        and tuple_info.element_types[i] == BaseType.INTEGER
                    ):
                        item_value = f"({item_value} as {exact_type_to_rust(symbol.exact_type, BaseType.FLOAT)})"
                    lines.append(self._render_identifier_assignment(name, symbol, item_value, include_type=True))
                return "\n".join(lines)
            return self._render_broadcast_assignment(ctx, target_ctx.tupleAssignmentTarget(), ctx.expression(), value, include_type=True)

        token = target_ctx.IDENTIFIER()
        var_name = token.getText()
        symbol = self.symbols.lookup_by_interval(token.getSourceInterval(), self._current_function)
        value = self._visit_expression_with_expectations(
            ctx.expression(),
            expected_type=symbol.resolved_type if symbol else None,
            dict_info=symbol.dict_info if symbol else None,
            set_info=symbol.set_info if symbol else None,
            tuple_info=symbol.tuple_info if symbol else None,
            callable_info=symbol.callable_info if symbol else None,
            coerce_scalar=False,
        )
        if symbol is not None:
            value = self._coerce_numeric_rhs_for_target(value, ctx.expression(), symbol.resolved_type, symbol.exact_type)
        if symbol is None:
            return f"let {var_name} = {value};"

        return self._render_identifier_assignment(var_name, symbol, value, include_type=True)

    def visitVariableAssignment(self, ctx: ZincParser.VariableAssignmentContext) -> str:
        """Visit variable assignment with shadowing support."""
        target = ctx.assignmentTarget().getText()
        target_ctx = ctx.assignmentTarget()
        expr = ctx.expression()
        assignment_op = ctx.assignmentOperator().getText()

        if assignment_op != "=":
            return self._render_compound_assignment(ctx, assignment_op)

        if target_ctx.tupleAssignmentTarget() and isinstance(expr, ZincParser.ChannelReceiveExprContext):
            names = self._binding_names(target_ctx.tupleAssignmentTarget())
            target_symbols = [
                self.symbols.lookup_by_interval(token.getSourceInterval(), self._current_function)
                for token in target_ctx.tupleAssignmentTarget().getTokens(ZincParser.IDENTIFIER)
            ]
            needs_declaration = any(symbol is None or symbol.is_shadow or symbol.id not in self._declared_vars for symbol in target_symbols)
            pattern_names = []
            for name, symbol in zip(names, target_symbols, strict=False):
                if needs_declaration and symbol and symbol.is_mutated:
                    pattern_names.append(f"mut {name}")
                else:
                    pattern_names.append(name)
                if needs_declaration:
                    self._declared_vars.add(name)
            pattern = self._render_tuple_pattern(pattern_names)
            channel_value = self.visit(expr.expression())
            value_expr = (
                f"match {channel_value}.recv_option().await {{ Some(value) => (value, true), None => (Default::default(), false), }}"
            )
            if needs_declaration:
                return f"let {pattern} = {value_expr};"
            return f"{pattern} = {value_expr};"

        # Check if this is a chan() call - generate tuple destructuring
        if isinstance(expr, ZincParser.FunctionCallExprContext):
            callee = expr.expression()
            if isinstance(callee, ZincParser.PrimaryExprContext):
                primary = callee.primaryExpression()
                if primary and primary.IDENTIFIER() and primary.IDENTIFIER().getText() == "chan":
                    var_name = target
                    capacity = None
                    chan_args = self._call_args_for_ctx(expr)
                    if chan_args:
                        capacity = self._visit_call_arg(chan_args[0])
                    # Look up channel info to get element type
                    if var_name in self._channel_infos:
                        chan_info = self._channel_infos[var_name]
                        constructor = "__ZincChannel"
                        if chan_info.element_type != BaseType.UNKNOWN:
                            constructor = f"__ZincChannel::<{chan_info.element_rust_type()}>"
                        self._declared_vars.add(var_name)
                        if chan_info.is_bounded and capacity is not None:
                            return f"let {var_name} = {constructor}::bounded({capacity});"
                        return f"let {var_name} = {constructor}::unbounded();"
                    else:
                        # Fallback - unknown element type
                        self._declared_vars.add(var_name)
                        if capacity is not None:
                            return f"let {var_name} = __ZincChannel::bounded({capacity});"
                        return f"let {var_name} = __ZincChannel::unbounded();"

        target_symbol = None
        if target_ctx.IDENTIFIER():
            target_symbol = self.symbols.lookup_by_interval(target_ctx.IDENTIFIER().getSourceInterval(), self._current_function)

        previous_dict_info = self._expected_dict_info
        previous_set_info = self._expected_set_info
        previous_tuple_info = self._expected_tuple_info
        value = self._visit_expression_with_expectations(
            expr,
            expected_type=target_symbol.resolved_type if target_symbol else None,
            dict_info=target_symbol.dict_info if target_symbol else None,
            set_info=target_symbol.set_info if target_symbol else None,
            tuple_info=target_symbol.tuple_info if target_symbol else None,
            callable_info=target_symbol.callable_info if target_symbol else None,
            coerce_scalar=False,
        )
        self._expected_dict_info = previous_dict_info
        self._expected_set_info = previous_set_info
        self._expected_tuple_info = previous_tuple_info

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

        captured_target = target_symbol is not None and self._symbol_is_captured_cell(target_symbol)
        storage_name = self._symbol_storage_unique_name(target_symbol) if captured_target and target_symbol is not None else None
        rendered_target = self._rust_binding_name(storage_name) if storage_name is not None else target
        if storage_name in self._captured_binding_names:
            value = f"Arc::new(Mutex::new({value}))" if (target_symbol.is_shadow or target not in self._declared_vars) else value

        if target_ctx.tupleAssignmentTarget():
            expr_type = self._get_expr_type(expr)
            tuple_info = self._get_tuple_info(expr)
            if expr_type != BaseType.TUPLE or tuple_info is None:
                return self._render_broadcast_assignment(ctx, target_ctx.tupleAssignmentTarget(), expr, value)
            names = self._binding_names(target_ctx.tupleAssignmentTarget())
            target_symbols = [
                self._symbol_for_binding_token(token)
                for token in target_ctx.tupleAssignmentTarget().getTokens(ZincParser.IDENTIFIER)
            ]
            needs_declaration = any(symbol is None or symbol.is_shadow or symbol.id not in self._declared_vars for symbol in target_symbols)
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
                collection_symbol = self._get_expr_symbol(index_access.expression(0))
                if collection_symbol is None and isinstance(index_access.expression(0), ZincParser.PrimaryExprContext):
                    primary = index_access.expression(0).primaryExpression()
                    if primary and primary.IDENTIFIER():
                        collection_symbol = self._lookup_identifier_symbol(primary.IDENTIFIER().getText())
                if collection_symbol and self._symbol_is_captured_cell(collection_symbol):
                    storage_name = self._symbol_storage_unique_name(collection_symbol)
                    collection = (
                        f"{self._rust_binding_name(storage_name)}.lock().unwrap()"
                        if storage_name
                        else self.visit(index_access.expression(0))
                    )
                else:
                    collection = self.visit(index_access.expression(0))
                key_ctx = index_access.expression(1)
                key = self._coerce_owned(self.visit(key_ctx), info.key_type, key_ctx)
                coerced_value = self._coerce_owned(value, info.value_type, expr)
                if collection_symbol and self._symbol_is_captured_cell(collection_symbol):
                    key_temp = self._staged_temp_name("captured_key", key_ctx)
                    value_temp = self._staged_temp_name("captured_value", expr)
                    return f"let {key_temp} = {key};\nlet {value_temp} = {coerced_value};\n{collection}.insert({key_temp}, {value_temp});"
                return f"{collection}.insert({key}, {coerced_value});"

        if target_ctx.IDENTIFIER():
            var_name = target
            symbol = target_symbol

            if symbol is None:
                # Fallback - shouldn't happen
                return f"let {var_name} = {value};"

            if self._symbol_is_captured_cell(symbol) and (
                symbol.is_captured_ref or not (symbol.is_shadow or var_name not in self._declared_vars)
            ):
                storage_name = self._symbol_storage_unique_name(symbol)
                if storage_name is None:
                    return 'panic!("missing captured binding");'
                temp_name = self._staged_temp_name("captured_write", ctx)
                return f"let {temp_name} = {value};\n*{self._rust_binding_name(storage_name)}.lock().unwrap() = {temp_name};"

            if symbol.is_shadow or var_name not in self._declared_vars:
                # First declaration OR shadow (type change) -> use let
                self._declared_vars.add(var_name)
                # Check if this is a struct var that needs mut
                needs_mut = symbol.is_mutated or var_name in self._mut_struct_vars
                if needs_mut:
                    return f"let mut {rendered_target} = {value};"
                return f"let {rendered_target} = {value};"
            else:
                # Same-type reassignment -> bare assignment
                return f"{rendered_target} = {value};"

        if target_ctx.memberAccess():
            member_ctx = target_ctx.memberAccess()
            receiver_ctx = member_ctx.expression()
            receiver_symbol = self._get_expr_symbol(receiver_ctx)
            if receiver_symbol is None and isinstance(receiver_ctx, ZincParser.PrimaryExprContext):
                primary = receiver_ctx.primaryExpression()
                if primary and primary.IDENTIFIER():
                    receiver_symbol = self._lookup_identifier_symbol(primary.IDENTIFIER().getText())
            if receiver_symbol and self._symbol_is_captured_cell(receiver_symbol):
                storage_name = self._symbol_storage_unique_name(receiver_symbol)
                if storage_name is not None:
                    temp_name = self._staged_temp_name("captured_field", ctx)
                    return (
                        f"let {temp_name} = {value};\n"
                        f"{self._rust_binding_name(storage_name)}.lock().unwrap()."
                        f"{member_ctx.IDENTIFIER().getText()} = {temp_name};"
                    )

        return f"{target} = {value};"

    def _render_compound_assignment(self, ctx: ZincParser.VariableAssignmentContext, assignment_op: str) -> str:
        """Render numeric compound assignment operators."""
        target_ctx = ctx.assignmentTarget()
        expr = ctx.expression()
        target = target_ctx.getText()
        target_symbol = None
        if target_ctx.IDENTIFIER():
            target_symbol = self.symbols.lookup_by_interval(target_ctx.IDENTIFIER().getSourceInterval(), self._current_function)

        target_type = target_symbol.resolved_type if target_symbol else self._get_expr_type(target_ctx)
        target_exact_type = target_symbol.exact_type if target_symbol else self._get_expr_exact_type(target_ctx)
        value = self._visit_expression_with_expectations(
            expr,
            expected_type=target_type if target_type != BaseType.UNKNOWN else None,
            coerce_scalar=False,
        )
        if assignment_op != "**=":
            value = self._coerce_numeric_rhs_for_target(value, expr, target_type, target_exact_type)

        if target_ctx.IDENTIFIER() and target_symbol is not None and self._symbol_is_captured_cell(target_symbol):
            storage_name = self._symbol_storage_unique_name(target_symbol)
            if storage_name is None:
                return 'panic!("missing captured binding");'
            rust_target = self._rust_binding_name(storage_name)
            value_temp = self._staged_temp_name("captured_compound", expr)
            lines = [f"let {value_temp} = {value};"]
            if assignment_op == "**=":
                guard_name = self._staged_temp_name("captured_guard", target_ctx)
                power_value = self._render_power_assignment_expr(f"*{guard_name}", target_type, target_exact_type, value_temp, expr)
                lines.extend(
                    [
                        "{",
                        f"    let mut {guard_name} = {rust_target}.lock().unwrap();",
                        f"    *{guard_name} = {power_value};",
                        "}",
                    ]
                )
                return "\n".join(lines)
            lines.append(f"*{rust_target}.lock().unwrap() {assignment_op} {value_temp};")
            return "\n".join(lines)

        if assignment_op == "**=":
            power_value = self._render_power_assignment_expr(target, target_type, target_exact_type, value, expr)
            return f"{target} = {power_value};"
        return f"{target} {assignment_op} {value};"

    def _render_power_assignment_expr(
        self,
        target: str,
        target_type: BaseType,
        target_exact_type: str | None,
        right: str,
        right_ctx,
    ) -> str:
        """Render the RHS for exponentiation assignment."""
        if target_type == BaseType.FLOAT:
            float_exact = exact_type_to_rust(target_exact_type, BaseType.FLOAT)
            right_type = self._get_expr_type(right_ctx)
            if right_type == BaseType.INTEGER:
                right = f"({right} as {float_exact})"
            return f"({target}).powf({right})"
        return f"({target}).pow(({right}) as u32)"

    def visitIfExpr(self, ctx: ZincParser.IfExprContext) -> str:
        """Visit an if-expression wrapper."""
        return self.visit(ctx.ifExpression())

    def visitIfExpression(self, ctx: ZincParser.IfExpressionContext) -> str:
        """Visit an expression-form if and lower it to a Rust if expression."""
        expr_symbol = self._get_expr_symbol(ctx)
        expected_type = self._expected_type_for_expression(ctx)
        expected_callable_info = self._expected_callable_for_expression(ctx)
        previous_result_type = self._expected_result_type
        previous_callable_info = self._expected_callable_info
        previous_dict_info = self._expected_dict_info
        previous_set_info = self._expected_set_info
        previous_tuple_info = self._expected_tuple_info
        if expected_type is not None:
            self._expected_result_type = expected_type
        if expected_callable_info is not None:
            self._expected_callable_info = expected_callable_info
        if expr_symbol and expr_symbol.dict_info:
            self._expected_dict_info = expr_symbol.dict_info
        if expr_symbol and expr_symbol.set_info:
            self._expected_set_info = expr_symbol.set_info
        if expr_symbol and expr_symbol.tuple_info:
            self._expected_tuple_info = expr_symbol.tuple_info
        try:
            conditions, blocks, else_block = self._flatten_if_expression(ctx)
            return self._render_if_chain(conditions, blocks, else_block, as_expression=True)
        finally:
            self._expected_result_type = previous_result_type
            self._expected_callable_info = previous_callable_info
            self._expected_dict_info = previous_dict_info
            self._expected_set_info = previous_set_info
            self._expected_tuple_info = previous_tuple_info

    def _render_if_statement(self, ctx: ZincParser.IfStatementContext, *, as_expression: bool) -> str:
        """Render a statement-form if chain."""
        expressions = list(ctx.expression())
        blocks = list(ctx.block())
        else_block = blocks[-1] if len(blocks) > len(expressions) else None
        then_blocks = blocks[: len(expressions)]
        return self._render_if_chain(expressions, then_blocks, else_block, as_expression=as_expression)

    def visitIfStatement(self, ctx: ZincParser.IfStatementContext) -> str:
        """Visit if statement."""
        return self._render_if_statement(ctx, as_expression=False)

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
        binding_symbols = [
            self.symbols.lookup_by_interval(token.getSourceInterval(), self._current_function)
            for token in binding_ctx.getTokens(ZincParser.IDENTIFIER)
        ]
        raw_loop_value = f"__zinc_for_value_{self._next_select_id()}"
        has_captured_binding = any(symbol is not None and symbol.unique_name in self._captured_binding_names for symbol in binding_symbols)
        loop_pattern = names[0] if len(names) == 1 else self._render_tuple_pattern(names)
        loop_header_pattern = loop_pattern
        loop_prelude: list[str] = []
        if has_captured_binding:
            if len(names) == 1:
                loop_header_pattern = raw_loop_value
                box_line = self._captured_binding_box_line(binding_symbols[0], raw_loop_value)
                if box_line is not None:
                    loop_prelude.append(box_line)
            else:
                loop_header_pattern = raw_loop_value
                raw_pattern = self._render_tuple_pattern(names)
                loop_prelude.append(f"let {raw_pattern} = {raw_loop_value};")
                for name, symbol in zip(names, binding_symbols, strict=False):
                    box_line = self._captured_binding_box_line(symbol, name)
                    if box_line is not None:
                        loop_prelude.append(box_line)
        body_stmts = self._generate_block(ctx.block())

        if self._get_expr_type(ctx.expression()) == BaseType.CHANNEL:
            loop_id = self._next_select_id()
            channel_iter = f"__zinc_channel_iter_{loop_id}"
            iterable_expr = self.visit(ctx.expression())
            lines = [
                "{",
                f"    let {channel_iter} = {iterable_expr}.clone();",
                "    loop {",
                f"        let Some({loop_header_pattern}) = {channel_iter}.recv_option().await else {{",
                "            break;",
                "        };",
            ]
            for stmt in loop_prelude:
                lines.append(f"        {stmt}")
            for stmt in body_stmts:
                for line in stmt.split("\n"):
                    lines.append(f"        {line}")
            lines.append("    }")
            lines.append("}")
            return "\n".join(lines)

        iterable = self._render_for_iterable(ctx.expression())

        lines = [f"for {loop_header_pattern} in {iterable} {{"]
        for stmt in loop_prelude:
            lines.append(f"    {stmt}")
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

    def _render_select_case_body(
        self,
        block_ctx,
        prelude: list[str] | None = None,
        local_names: set[str] | None = None,
    ) -> list[str]:
        """Render a select case body, keeping header bindings local to the case."""
        return self._render_scoped_block(block_ctx, prelude=prelude, local_names=local_names)

    def _select_receive_binding(self, case_ctx) -> tuple[str, list[str]]:
        """Return the binding mode for a receive case."""
        binding_ctx = case_ctx.selectReceiveBinding()
        if binding_ctx is None:
            return "none", []
        if binding_ctx.IDENTIFIER():
            return "single", [binding_ctx.IDENTIFIER().getText()]
        return "status", self._binding_names(binding_ctx.tupleAssignmentTarget())

    def _render_select_receive_case_body(self, case_ctx, option_expr: str) -> list[str]:
        """Render a receive-case body from an Option-valued receive result."""
        mode, names = self._select_receive_binding(case_ctx)
        if mode == "none":
            return self._render_select_case_body(case_ctx.block())
        if mode == "single":
            prelude = [
                f'let {names[0]} = match {option_expr} {{ Some(value) => value, None => panic!("select receive on closed channel") }};'
            ]
            return self._render_select_case_body(case_ctx.block(), prelude=prelude, local_names={names[0]})
        pattern = self._render_tuple_pattern(names)
        prelude = [f"let {pattern} = match {option_expr} {{ Some(value) => (value, true), None => (Default::default(), false) }};"]
        return self._render_select_case_body(case_ctx.block(), prelude=prelude, local_names=set(names))

    def _render_select_without_default(self, case_ctxs: list, select_id: int) -> str:
        """Lower a blocking select to tokio::select!."""
        lines = ["tokio::select! {"]
        for branch_index, case_ctx in enumerate(case_ctxs):
            if isinstance(case_ctx, ZincParser.SelectReceiveCaseContext):
                recv_name = f"__zinc_select_value_{select_id}_{branch_index}"
                receiver = self.visit(case_ctx.expression())
                body = self._render_select_receive_case_body(case_ctx, recv_name)
                lines.append(f"    {recv_name} = async {{ {receiver}.recv_option().await }} => {{")
                self._append_block_lines(lines, body, 2)
                lines.append("    },")
                continue

            channel_name = case_ctx.IDENTIFIER().getText()
            sender = self._channel_sender_expr(channel_name)
            value = self._render_channel_value(channel_name, case_ctx.expression())
            body = self._render_select_case_body(case_ctx.block())
            result_name = f"__zinc_select_result_{select_id}_{branch_index}"
            lines.append(f"    {result_name} = async {{ {sender}.send({value}).await }} => {{")
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
                value_name = f"__zinc_select_value_{select_id}_{branch_index}"
                receiver = self.visit(case_ctx.expression())
                mode, _ = self._select_receive_binding(case_ctx)
                body_with_value = self._render_select_receive_case_body(case_ctx, f"Some({value_name})")
                body_closed = self._render_select_receive_case_body(case_ctx, "None")
                lines.append(f"                match {receiver}.try_recv() {{")
                lines.append(f"                    __ZincTryRecv::Value({value_name}) => {{")
                self._append_block_lines(lines, body_with_value, 6)
                lines.append(f"                        break {label};")
                lines.append("                    },")
                lines.append("                    __ZincTryRecv::Empty => {},")
                if mode == "single":
                    lines.append('                    __ZincTryRecv::Closed => panic!("select receive on closed channel"),')
                else:
                    lines.append("                    __ZincTryRecv::Closed => {")
                    self._append_block_lines(lines, body_closed, 6)
                    lines.append(f"                        break {label};")
                    lines.append("                    },")
                lines.append("                }")
            else:
                channel_name = case_ctx.IDENTIFIER().getText()
                sender = self._channel_sender_expr(channel_name)
                value = self._render_channel_value(channel_name, case_ctx.expression())
                body = self._render_select_case_body(case_ctx.block())
                lines.append(f"                match {sender}.try_send({value}) {{")
                lines.append("                    __ZincTrySend::Sent => {")
                self._append_block_lines(lines, body, 6)
                lines.append(f"                        break {label};")
                lines.append("                    },")
                lines.append("                    __ZincTrySend::Full(_) => {},")
                lines.append('                    __ZincTrySend::Closed(_) => panic!("select send on closed channel"),')
                lines.append("                }")
            lines.append("            }")

        lines.extend(
            [
                "            _ => unreachable!(),",
                "        }",
                "    }",
            ]
        )
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
        non_default_cases = [case_ctx for case_ctx in cases if not isinstance(case_ctx, ZincParser.SelectDefaultCaseContext)]
        if default_case is not None:
            return self._render_select_with_default(non_default_cases, default_case, select_id)
        return self._render_select_without_default(non_default_cases, select_id)

    def visitReturnStatement(self, ctx: ZincParser.ReturnStatementContext) -> str:
        """Visit return statement."""
        if ctx.expression():
            func = self.atlas.functions.get(self._current_function)
            value = self._visit_expression_with_expectations(
                ctx.expression(),
                expected_type=func.return_type if func else None,
                dict_info=func.return_dict_info if func else None,
                set_info=func.return_set_info if func else None,
                tuple_info=func.return_tuple_info if func else None,
                callable_info=func.return_callable_info if func else None,
            )
            return self._render_return(f"return {value};")
        return self._render_return("return;")

    def _render_return(self, return_stmt: str) -> str:
        """Render a return statement, awaiting local spawned tasks first."""
        if not self._spawn_handles_var:
            return return_stmt
        return "\n".join(
            [
                self._render_spawn_handle_awaits(self._spawn_handles_var),
                return_stmt,
            ]
        )

    def visitBreakStatement(self, ctx: ZincParser.BreakStatementContext) -> str:
        """Visit break statement."""
        return "break;"

    def visitContinueStatement(self, ctx: ZincParser.ContinueStatementContext) -> str:
        """Visit continue statement."""
        return "continue;"

    def visitFailStatement(self, ctx: ZincParser.FailStatementContext) -> str:
        """Visit fail statement."""
        value_expr = ctx.expression()
        value = self.visit(value_expr)
        value = self._coerce_to_value_spec(value, self._nearest_result_error_spec(ctx), value_expr)
        return f"return Err({value});"

    def visitSpawnStatement(self, ctx: ZincParser.SpawnStatementContext) -> str:
        """Visit spawn statement, using mangled name for spawned function."""
        self._uses_async = True
        # Grammar: spawn expression '(' argumentList? ')'
        # The expression is the function name, and args are in argumentList
        func_expr = ctx.expression()
        func_name = self.visit(func_expr)
        callee_symbol = self._get_expr_symbol(func_expr)
        args = []
        setup = []
        call_args = self._call_args_for_ctx(ctx)
        arg_ctxs = [self._call_arg_expr(arg) for arg in call_args]

        # Look up mangled name from specialization map (scoped by current function)
        key = (self._current_function, ctx.getSourceInterval())
        mangled = self._specialization_map.get(key)
        call_needs_await = False
        if mangled:
            func = self.atlas.functions.get(mangled)
            if func is not None:
                args = self._render_function_args_for_instance(func, call_args)
                setup, args = self._prepare_spawn_args(call_args, args)
                args = self._process_function_args(mangled, args, arg_ctxs)
            else:
                args = [self._visit_call_arg(arg) for arg in call_args]
                setup, args = self._prepare_spawn_args(call_args, args)
            if func is not None:
                closure_info = self._closure_info(func.qualified_name)
                if closure_info is not None:
                    args = [self._closure_env_constructor(closure_info), *args]
                call_needs_await = func.is_async
            call = f"{mangled}({', '.join(args)})"
        elif callee_symbol and callee_symbol.callable_info:
            args = self._render_callable_args_for_signature(callee_symbol.callable_info, call_args)
            setup, args = self._prepare_spawn_args(call_args, args)
            args = self._process_callable_args(
                callee_symbol.callable_info,
                args,
                arg_ctxs,
            )
            callable_expr = func_name
            if self._is_direct_callable_expr(func_expr, callee_symbol):
                callable_expr = self._render_callable_value(callee_symbol.callable_info)
            call = f"{callable_expr}.call({', '.join(args)})"
        else:
            args = [self._visit_call_arg(arg) for arg in call_args]
            setup, args = self._prepare_spawn_args(call_args, args)
            call = f"{func_name}({', '.join(args)})"
        async_call = f"{call}.await" if call_needs_await else call
        if setup:
            task = f"tokio::spawn({{ {' '.join(setup)} async move {{ {async_call}; }} }})"
        else:
            task = f"tokio::spawn(async move {{ {async_call}; }})"
        if self._spawn_handles_var:
            return f"{self._spawn_handles_var}.push({task});"
        return f"{task}.await.unwrap();"

    def visitChannelSendStatement(self, ctx: ZincParser.ChannelSendStatementContext) -> str:
        """Visit channel send statement."""
        channel_name = ctx.IDENTIFIER().getText()
        sender = self._channel_sender_expr(channel_name)
        value = self._render_channel_value(channel_name, ctx.expression())
        return f"{sender}.send({value}).await;"

    def visitExpressionStatement(self, ctx: ZincParser.ExpressionStatementContext) -> str:
        """Visit expression statement."""
        expr = self.visit(ctx.expression())
        if expr.endswith(";"):
            return expr
        return f"{expr};"

    def visitStatement(self, ctx: ZincParser.StatementContext) -> str | None:
        """Visit a statement - dispatch to specific visitor."""
        return self.visitChildren(ctx)
