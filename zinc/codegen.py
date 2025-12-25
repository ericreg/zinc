"""Code generation for the Zinc compiler."""

import re
from dataclasses import dataclass, field

from zinc.parser.zincVisitor import zincVisitor
from zinc.parser.zincParser import zincParser as ZincParser
from zinc.atlas import Atlas, FunctionInstance, StructInstance, ConstInstance, StructFieldInfo, StructMethodInfo
from zinc.symbols import SymbolTable, SymbolKind
from zinc.ast.types import BaseType, type_to_rust, ChannelTypeInfo


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
        specialization_map: dict[tuple[int, int], str] | None = None,
        channel_infos: dict[str, ChannelTypeInfo] | None = None,
    ):
        self.atlas = atlas
        self.symbols = symbols
        self._specialization_map = specialization_map or {}
        self._channel_infos = channel_infos or {}  # var_name -> ChannelTypeInfo
        self._uses_async = False
        self._current_function: str | None = None
        self._declared_vars: set[str] = set()
        self._indent_level = 0
        # Struct tracking
        self._struct_instance_vars: dict[str, str] = {}  # var_name -> struct_name
        self._mut_struct_vars: set[str] = set()  # vars that need `let mut`
        self._current_struct: str | None = None  # When generating struct method
        self._current_struct_fields: dict[str, StructFieldInfo] | None = None
        # Track variables that hold compile-time literal values
        self._literal_vars: set[str] = set()

    def generate(self) -> RustProgram:
        """Main entry point - generate Rust code for all reachable code."""
        # Pre-scan to determine which struct vars need mut
        self._prescan_for_mut_vars()

        imports = self._generate_imports()
        consts = [self._generate_const(c) for c in self.atlas.consts.values()]
        structs = [self._generate_struct(s) for s in self.atlas.structs.values()]
        functions = []
        main_body = []

        for func_name in self.atlas.topological_order():
            func = self.atlas.functions[func_name]
            if func.name == "main":
                self._current_function = "main"
                self._declared_vars.clear()
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
        main_func = self.atlas.functions.get("main")
        if main_func:
            self._prescan_block(main_func.ctx.block())

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
                    self._struct_instance_vars[var_name] = struct_name
                # Track if variable is assigned a compile-time literal value
                elif self._is_compile_time_literal_expr(expr):
                    self._literal_vars.add(var_name)

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

    def _detect_struct_assignment(self, expr_ctx) -> str | None:
        """Detect if expression assigns a struct instance, return struct name."""
        # Direct struct instantiation: Point { x: 1, y: 2 }
        if isinstance(expr_ctx, ZincParser.PrimaryExprContext):
            primary = expr_ctx.primaryExpression()
            if primary and primary.structInstantiation():
                return primary.structInstantiation().IDENTIFIER().getText()

        # Static method call returning Self: Counter.new(0)
        if isinstance(expr_ctx, ZincParser.FunctionCallExprContext):
            callee = expr_ctx.expression()
            if isinstance(callee, ZincParser.MemberAccessExprContext):
                target_text = callee.expression().getText()
                method_name = callee.IDENTIFIER().getText()
                struct = next((s for s in self.atlas.structs.values() if s.name == target_text), None)
                if struct:
                    method = next((m for m in struct.methods if m.name == method_name), None)
                    if method and method.return_type == "Self":
                        return target_text
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
                        if target_text in self._struct_instance_vars:
                            struct_name = self._struct_instance_vars[target_text]
                            struct = next((s for s in self.atlas.structs.values() if s.name == struct_name), None)
                            if struct:
                                method = next((m for m in struct.methods if m.name == method_name), None)
                                if method and method.self_mutability == "&mut self":
                                    self._mut_struct_vars.add(target_text)

    def _generate_imports(self) -> list[str]:
        """Generate import statements based on what's used."""
        imports = []
        if self._uses_async:
            imports.append("use tokio;")
        return imports

    def _generate_const(self, const: ConstInstance) -> str:
        """Generate a const declaration."""
        ctx: ZincParser.ConstDeclarationContext = const.ctx
        name = const.name
        value = self.visit(ctx.expression())
        symbol = self.symbols.lookup_by_id(name)
        if symbol:
            type_str = type_to_rust(symbol.resolved_type)
            return f"const {name.upper()}: {type_str} = {value};"
        return f"const {name.upper()} = {value};"

    def _generate_struct(self, struct: StructInstance) -> str:
        """Generate a struct definition and impl block."""
        lines = []

        # Struct definition
        lines.append(f"struct {struct.name} {{")
        for f in struct.fields:
            vis = "" if f.is_private else "pub "
            rust_type = f.rust_type()
            lines.append(f"    {vis}{f.name}: {rust_type},")
        lines.append("}")

        # Impl block (only if there are methods)
        if struct.methods:
            lines.append("")
            lines.append(f"impl {struct.name} {{")
            for method in struct.methods:
                method_code = self._generate_struct_method(method, struct)
                for line in method_code.split("\n"):
                    lines.append(f"    {line}")
            lines.append("}")

        return "\n".join(lines)

    def _generate_struct_method(self, method: StructMethodInfo, struct: StructInstance) -> str:
        """Generate a single struct method."""
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
        self._current_struct = struct.name
        self._current_struct_fields = {f.name: f for f in struct.fields}
        body_stmts = self._generate_block(method.body_ctx)
        self._current_struct = None
        self._current_struct_fields = None

        lines = [f"fn {method.name}({params}){ret_type} {{"]
        for stmt in body_stmts:
            for line in stmt.split("\n"):
                lines.append(f"    {line}")
        lines.append("}")

        return "\n".join(lines)

    def _zinc_type_to_rust(self, zinc_type: str) -> str:
        """Convert Zinc type annotation to Rust type."""
        mapping = {
            "i32": "i32",
            "i64": "i64",
            "f32": "f32",
            "f64": "f64",
            "string": "String",
            "bool": "bool",
        }
        return mapping.get(zinc_type.lower(), zinc_type)

    def _generate_function(self, func: FunctionInstance) -> str:
        """Generate a function definition using mangled name."""
        self._current_function = func.mangled_name
        self._declared_vars.clear()
        ctx: ZincParser.FunctionDeclarationContext = func.ctx

        # Get parameter names and types from func.arg_types
        params = []
        if ctx.parameterList():
            for i, param_ctx in enumerate(ctx.parameterList().parameter()):
                param_name = param_ctx.IDENTIFIER().getText()
                if i < len(func.arg_types):
                    # Check if this is a channel parameter with type info
                    if i in func.arg_channel_infos:
                        chan_info = func.arg_channel_infos[i]
                        type_str = chan_info.to_rust_sender()
                    else:
                        type_str = type_to_rust(func.arg_types[i])
                    params.append(f"{param_name}: {type_str}")
                else:
                    params.append(param_name)

        body_stmts = self._generate_function_body(func)
        param_str = ", ".join(params)

        # Build return type suffix if not void
        if func.return_type != BaseType.VOID:
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
        return self._generate_block(ctx.block())

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
        args = ", ".join(interpolations)
        return f'format!("{format_str}", {args})'

    def visitPrimaryExpression(self, ctx: ZincParser.PrimaryExpressionContext) -> str:
        """Visit a primary expression."""
        if ctx.literal():
            return self.visit(ctx.literal())
        if ctx.IDENTIFIER():
            return ctx.IDENTIFIER().getText()
        if ctx.arrayLiteral():
            return self.visit(ctx.arrayLiteral())
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

    def visitParenExpr(self, ctx: ZincParser.ParenExprContext) -> str:
        """Visit parenthesized expression."""
        return f"({self.visit(ctx.expression())})"

    def visitAdditiveExpr(self, ctx: ZincParser.AdditiveExprContext) -> str:
        """Visit addition/subtraction expression."""
        left = self.visit(ctx.expression(0))
        op = ctx.getChild(1).getText()
        right = self.visit(ctx.expression(1))
        return f"({left} {op} {right})"

    def visitMultiplicativeExpr(self, ctx: ZincParser.MultiplicativeExprContext) -> str:
        """Visit multiplication/division expression."""
        left = self.visit(ctx.expression(0))
        op = ctx.getChild(1).getText()
        right = self.visit(ctx.expression(1))
        return f"({left} {op} {right})"

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
        return f"({left} {op} {right})"

    def visitEqualityExpr(self, ctx: ZincParser.EqualityExprContext) -> str:
        """Visit equality comparison."""
        left = self.visit(ctx.expression(0))
        op = ctx.getChild(1).getText()
        right = self.visit(ctx.expression(1))
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

    def visitIndexAccessExpr(self, ctx: ZincParser.IndexAccessExprContext) -> str:
        """Visit index access."""
        array = self.visit(ctx.expression(0))
        index = self.visit(ctx.expression(1))
        return f"{array}[{index}]"

    def visitRangeExpr(self, ctx: ZincParser.RangeExprContext) -> str:
        """Visit range expression."""
        start = self.visit(ctx.expression(0))
        end = self.visit(ctx.expression(1))
        if ctx.getChild(1).getText() == "..=":
            return f"{start}..={end}"
        return f"{start}..{end}"

    def visitMemberAccessExpr(self, ctx: ZincParser.MemberAccessExprContext) -> str:
        """Visit member access - could be field access or static method reference."""
        target_text = ctx.expression().getText()
        member = ctx.IDENTIFIER().getText()

        # Check if target is a struct type (for static method calls)
        struct_names = [s.name for s in self.atlas.structs.values()]
        if target_text in struct_names:
            # Return struct::method format for function call handler
            return f"{target_text}::{member}"

        # Regular member access (field or instance method)
        obj = self.visit(ctx.expression())
        return f"{obj}.{member}"

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

        if callee == "print":
            return self._render_print_call(args)

        # Static method call (StructName::method)
        if "::" in callee:
            struct_name, method_name = callee.split("::")
            struct = next((s for s in self.atlas.structs.values() if s.name == struct_name), None)
            if struct:
                args = self._process_method_args(struct, method_name, args, arg_ctxs)
            return f"{callee}({', '.join(args)})"

        # Instance method call (obj.method) - already visited, callee is "obj.method"
        if isinstance(callee_ctx, ZincParser.MemberAccessExprContext):
            # Check if this is an instance method on a struct variable
            target_ctx = callee_ctx.expression()
            method_name = callee_ctx.IDENTIFIER().getText()
            if isinstance(target_ctx, ZincParser.PrimaryExprContext):
                primary = target_ctx.primaryExpression()
                if primary and primary.IDENTIFIER():
                    target_var = primary.IDENTIFIER().getText()
                    if target_var in self._struct_instance_vars:
                        struct_name = self._struct_instance_vars[target_var]
                        struct = next((s for s in self.atlas.structs.values() if s.name == struct_name), None)
                        if struct:
                            args = self._process_method_args(struct, method_name, args, arg_ctxs)
            return f"{callee}({', '.join(args)})"

        # Look up mangled name from specialization map
        mangled = self._specialization_map.get(ctx.getSourceInterval())
        if mangled:
            return f"{mangled}({', '.join(args)})"

        return f"{callee}({', '.join(args)})"

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
                expr_args = ", ".join(interpolations)
                return f'println!("{format_str}", {expr_args})'
            return f'println!("{inner}")'
        return f"println!(\"{{}}\", {arg})"


    def visitChannelReceiveExpr(self, ctx: ZincParser.ChannelReceiveExprContext) -> str:
        """Visit channel receive expression."""
        # Get the channel variable name and use _rx suffix
        chan_expr = ctx.expression()
        if isinstance(chan_expr, ZincParser.PrimaryExprContext):
            primary = chan_expr.primaryExpression()
            if primary and primary.IDENTIFIER():
                chan_name = primary.IDENTIFIER().getText()
                # Check if this is a channel we created (in main)
                if chan_name in self._channel_infos:
                    return f"{chan_name}_rx.recv().await.unwrap()"
        receiver = self.visit(chan_expr)
        return f"{receiver}.recv().await.unwrap()"

    def visitStructInstantiation(self, ctx: ZincParser.StructInstantiationContext) -> str:
        """Visit struct instantiation."""
        name = ctx.IDENTIFIER().getText()

        # Get provided field values
        provided_fields: dict[str, str] = {}
        for field_ctx in ctx.fieldInit():
            field_name = field_ctx.IDENTIFIER().getText()
            field_value = self.visit(field_ctx.expression())
            provided_fields[field_name] = field_value

        # Look up struct definition to get all fields with defaults
        struct = next((s for s in self.atlas.structs.values() if s.name == name), None)
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

        # Check if this is a chan() call - generate tuple destructuring
        expr = ctx.expression()
        if isinstance(expr, ZincParser.FunctionCallExprContext):
            callee = expr.expression()
            if isinstance(callee, ZincParser.PrimaryExprContext):
                primary = callee.primaryExpression()
                if primary and primary.IDENTIFIER() and primary.IDENTIFIER().getText() == "chan":
                    var_name = target
                    # Look up channel info to get element type
                    if var_name in self._channel_infos:
                        chan_info = self._channel_infos[var_name]
                        elem_type = type_to_rust(chan_info.element_type)
                        self._declared_vars.add(var_name)
                        return f"let ({var_name}_tx, mut {var_name}_rx) = tokio::sync::mpsc::unbounded_channel::<{elem_type}>();"
                    else:
                        # Fallback - unknown element type
                        self._declared_vars.add(var_name)
                        return f"let ({var_name}_tx, mut {var_name}_rx) = tokio::sync::mpsc::unbounded_channel();"

        value = self.visit(expr)

        if ctx.assignmentTarget().IDENTIFIER():
            var_name = target
            identifier = ctx.assignmentTarget().IDENTIFIER()
            symbol = self.symbols.lookup_by_interval(identifier.getSourceInterval())

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
                lines.append(f"    {stmt}")

        if len(blocks) > len(expressions):
            lines.append("} else {")
            body_stmts = self._generate_block(blocks[-1])
            for stmt in body_stmts:
                lines.append(f"    {stmt}")

        lines.append("}")
        return "\n".join(lines)

    def visitForStatement(self, ctx: ZincParser.ForStatementContext) -> str:
        """Visit for loop."""
        var_name = ctx.IDENTIFIER().getText()
        iterable = self.visit(ctx.expression())
        body_stmts = self._generate_block(ctx.block())

        lines = [f"for {var_name} in {iterable} {{"]
        for stmt in body_stmts:
            lines.append(f"    {stmt}")
        lines.append("}")
        return "\n".join(lines)

    def visitWhileStatement(self, ctx: ZincParser.WhileStatementContext) -> str:
        """Visit while loop."""
        cond = self.visit(ctx.expression())
        body_stmts = self._generate_block(ctx.block())

        lines = [f"while {cond} {{"]
        for stmt in body_stmts:
            lines.append(f"    {stmt}")
        lines.append("}")
        return "\n".join(lines)

    def visitLoopStatement(self, ctx: ZincParser.LoopStatementContext) -> str:
        """Visit infinite loop."""
        body_stmts = self._generate_block(ctx.block())

        lines = ["loop {"]
        for stmt in body_stmts:
            lines.append(f"    {stmt}")
        lines.append("}")
        return "\n".join(lines)

    def visitReturnStatement(self, ctx: ZincParser.ReturnStatementContext) -> str:
        """Visit return statement."""
        if ctx.expression():
            value = self.visit(ctx.expression())
            return f"return {value};"
        return "return;"

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
        if ctx.argumentList():
            for arg in ctx.argumentList().expression():
                arg_code = self.visit(arg)
                # Check if this argument is a channel - use _tx suffix
                if isinstance(arg, ZincParser.PrimaryExprContext):
                    primary = arg.primaryExpression()
                    if primary and primary.IDENTIFIER():
                        var_name = primary.IDENTIFIER().getText()
                        if var_name in self._channel_infos:
                            arg_code = f"{var_name}_tx"
                args.append(arg_code)

        # Look up mangled name from specialization map
        mangled = self._specialization_map.get(ctx.getSourceInterval())
        if mangled:
            call = f"{mangled}({', '.join(args)})"
        else:
            call = f"{func_name}({', '.join(args)})"
        return f"tokio::spawn({call});"

    def visitChannelSendStatement(self, ctx: ZincParser.ChannelSendStatementContext) -> str:
        """Visit channel send statement."""
        sender = ctx.IDENTIFIER().getText()
        value = self.visit(ctx.expression())
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
