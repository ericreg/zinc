"""Symbol Table for the Zinc compiler."""

from dataclasses import dataclass
from enum import Enum, auto

from antlr4 import ParserRuleContext

from zinc.ast.types import BaseType, TypeInfo, parse_literal
from zinc.parser.zincVisitor import zincVisitor
from zinc.parser.zincParser import zincParser as ZincParser
from zinc.atlas import Atlas, FunctionInstance, ConstInstance


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
    unique_name: str  # Scoped unique name (e.g., "main.a", "tmp_0")
    kind: SymbolKind
    resolved_type: BaseType
    source_interval: tuple[int, int]  # ANTLR source interval (start, stop)


class SymbolTable:
    """Scoped symbol table with lookup by id or source interval."""

    def __init__(self):
        self._symbols: list[Symbol] = []
        self._by_interval: dict[str, Symbol] = {}  # "(start, stop)" -> Symbol
        self._scope_stack: list[dict[str, Symbol]] = [{}]  # Stack of id -> Symbol
        self._temp_counter: int = 0
        self._scope_path: list[str] = []  # e.g., ["main", "if_0"]

    @property
    def current_scope(self) -> str:
        """Return current scope path like 'main.if_0'."""
        return ".".join(self._scope_path) if self._scope_path else "global"

    def enter_scope(self, name: str) -> None:
        """Enter a new scope (function, if block, for loop, etc.)."""
        self._scope_path.append(name)
        self._scope_stack.append({})

    def exit_scope(self) -> None:
        """Exit current scope."""
        self._scope_path.pop()
        self._scope_stack.pop()

    def define(
        self,
        id: str,
        kind: SymbolKind,
        resolved_type: BaseType,
        interval: tuple[int, int],
    ) -> Symbol:
        """Define a named symbol in current scope."""
        unique_name = f"{self.current_scope}.{id}" if self._scope_path else id
        symbol = Symbol(
            id=id,
            unique_name=unique_name,
            kind=kind,
            resolved_type=resolved_type,
            source_interval=interval,
        )
        self._symbols.append(symbol)
        self._by_interval[f"({interval[0]}, {interval[1]})"] = symbol
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
        self._by_interval[f"({interval[0]}, {interval[1]})"] = symbol
        return symbol

    def lookup_by_id(self, id: str) -> Symbol | None:
        """Look up symbol by name in current and enclosing scopes."""
        for scope in reversed(self._scope_stack):
            if id in scope:
                return scope[id]
        return None

    def lookup_by_interval(self, interval: tuple[int, int]) -> Symbol | None:
        """Look up symbol by source interval."""
        key = f"({interval[0]}, {interval[1]})"
        return self._by_interval.get(key)

    def all_symbols(self) -> list[Symbol]:
        """Return all defined symbols."""
        return self._symbols.copy()


class SymbolTableVisitor(zincVisitor):
    """Walks reachable code and builds a SymbolTable."""

    def __init__(self, atlas: Atlas):
        self.atlas = atlas
        self.symbols = SymbolTable()
        self._block_counters: dict[str, int] = {}  # For unique block names

    def resolve(self) -> SymbolTable:
        """Main entry point - resolve types for all reachable code."""
        self._register_builtins()

        for const in self.atlas.consts.values():
            self._resolve_const(const)

        for mangled_name in self.atlas.topological_order():
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

    def _next_block_name(self, prefix: str) -> str:
        """Generate unique block name like 'if_0', 'for_1'."""
        count = self._block_counters.get(prefix, 0)
        self._block_counters[prefix] = count + 1
        return f"{prefix}_{count}"

    def _resolve_const(self, const: ConstInstance) -> None:
        """Resolve type of a global constant."""
        ctx: ZincParser.ConstDeclarationContext = const.ctx  # type: ignore[assignment]
        expr_type = self.visit(ctx.expression())
        self.symbols.define(
            id=const.name,
            kind=SymbolKind.CONST,
            resolved_type=expr_type,
            interval=ctx.getSourceInterval(),
        )

    def _resolve_function(self, func: FunctionInstance) -> None:
        """Resolve types within a function body."""
        self._block_counters.clear()
        self.symbols.enter_scope(func.name)
        self.visit(func.ctx)
        self.symbols.exit_scope()

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
                self.symbols.define_temp(
                    resolved_type=symbol.resolved_type,
                    interval=ctx.getSourceInterval(),
                )
                return symbol.resolved_type
            self.symbols.define_temp(
                resolved_type=BaseType.UNKNOWN,
                interval=ctx.getSourceInterval(),
            )
            return BaseType.UNKNOWN

        if ctx.arrayLiteral():
            return self.visit(ctx.arrayLiteral())

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
        self.symbols.define_temp(
            resolved_type=inner_type,
            interval=ctx.getSourceInterval(),
        )
        return inner_type

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
        """Visit array literal."""
        for expr_ctx in ctx.expression():
            self.visit(expr_ctx)
        self.symbols.define_temp(
            resolved_type=BaseType.ARRAY,
            interval=ctx.getSourceInterval(),
        )
        return BaseType.ARRAY

    def visitIndexAccessExpr(self, ctx: ZincParser.IndexAccessExprContext) -> BaseType:
        """Visit index access."""
        self.visit(ctx.expression(0))
        self.visit(ctx.expression(1))
        self.symbols.define_temp(
            resolved_type=BaseType.UNKNOWN,
            interval=ctx.getSourceInterval(),
        )
        return BaseType.UNKNOWN

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
        self.symbols.define_temp(
            resolved_type=BaseType.UNKNOWN,
            interval=ctx.getSourceInterval(),
        )
        return BaseType.UNKNOWN

    def visitFunctionCallExpr(self, ctx: ZincParser.FunctionCallExprContext) -> BaseType:
        """Visit function call expression."""
        callee_type = self.visit(ctx.expression())

        if ctx.argumentList():
            for arg_expr in ctx.argumentList().expression():
                self.visit(arg_expr)

        callee_ctx = ctx.expression()
        if isinstance(callee_ctx, ZincParser.PrimaryExprContext):
            primary = callee_ctx.primaryExpression()
            if primary and primary.IDENTIFIER():
                func_name = primary.IDENTIFIER().getText()
                func_symbol = self.symbols.lookup_by_id(func_name)
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

    def visitStructInstantiation(self, ctx: ZincParser.StructInstantiationContext) -> BaseType:
        """Visit struct literal."""
        for field_ctx in ctx.fieldInit():
            self.visit(field_ctx.expression())
        self.symbols.define_temp(
            resolved_type=BaseType.STRUCT,
            interval=ctx.getSourceInterval(),
        )
        return BaseType.STRUCT

    def visitVariableAssignment(self, ctx: ZincParser.VariableAssignmentContext) -> None:
        """Visit variable assignment and create symbol."""
        expr_type = self.visit(ctx.expression())
        target = ctx.assignmentTarget()
        var_name = target.getText()

        if target.IDENTIFIER():
            existing = self.symbols.lookup_by_id(var_name)
            if existing is None:
                self.symbols.define(
                    id=var_name,
                    kind=SymbolKind.VARIABLE,
                    resolved_type=expr_type,
                    interval=target.getSourceInterval(),
                )
            else:
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
        """Visit return statement."""
        if ctx.expression():
            self.visit(ctx.expression())

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

        block_name = self._next_block_name("for")
        self.symbols.enter_scope(block_name)

        loop_var = ctx.IDENTIFIER().getText()
        if iterable_type == BaseType.INTEGER:
            var_type = BaseType.INTEGER
        else:
            var_type = BaseType.UNKNOWN

        self.symbols.define(
            id=loop_var,
            kind=SymbolKind.VARIABLE,
            resolved_type=var_type,
            interval=(ctx.IDENTIFIER().getSourceInterval()),
        )

        self.visit(ctx.block())
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

    def visitFunctionDeclaration(self, ctx: ZincParser.FunctionDeclarationContext) -> None:
        """Visit function declaration."""
        if ctx.parameterList():
            for param_ctx in ctx.parameterList().parameter():
                param_name = param_ctx.IDENTIFIER().getText()
                self.symbols.define(
                    id=param_name,
                    kind=SymbolKind.PARAMETER,
                    resolved_type=BaseType.UNKNOWN,
                    interval=param_ctx.getSourceInterval(),
                )

        self.visit(ctx.block())

    def visitExpressionStatement(self, ctx: ZincParser.ExpressionStatementContext) -> None:
        """Visit expression statement."""
        self.visit(ctx.expression())
