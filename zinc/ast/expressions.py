"""Expression AST nodes for the Zinc compiler."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from .types import BaseType, TypeInfo


class Expression(ABC):
    """Base class for all expression nodes."""

    type_info: Optional[TypeInfo] = None

    @abstractmethod
    def render_rust(self) -> str:
        """Generate Rust code for this expression."""
        pass


@dataclass
class LiteralExpr(Expression):
    """Literal value (integer, float, string, boolean)."""

    value: str
    type_info: TypeInfo = field(default_factory=lambda: TypeInfo(BaseType.UNKNOWN))

    def render_rust(self) -> str:
        return self.value


@dataclass
class IdentifierExpr(Expression):
    """Variable reference."""

    name: str
    type_info: Optional[TypeInfo] = None

    def render_rust(self) -> str:
        return self.name


@dataclass
class BinaryExpr(Expression):
    """Binary operation (arithmetic, logical, comparison)."""

    left: Expression
    operator: str  # '+', '-', '*', '/', '%'
    right: Expression
    type_info: Optional[TypeInfo] = None

    def render_rust(self) -> str:
        left_code = self.left.render_rust()
        right_code = self.right.render_rust()
        return f"{left_code} {self.operator} {right_code}"


@dataclass
class UnaryExpr(Expression):
    """Unary operation (negation, not)."""

    operator: str  # '-', '!', 'not'
    operand: Expression
    type_info: Optional[TypeInfo] = None

    def render_rust(self) -> str:
        op = "!" if self.operator == "not" else self.operator
        return f"{op}{self.operand.render_rust()}"


@dataclass
class ParenExpr(Expression):
    """Parenthesized expression - preserves grouping."""

    inner: Expression
    type_info: Optional[TypeInfo] = None

    def render_rust(self) -> str:
        return f"({self.inner.render_rust()})"


@dataclass
class CallExpr(Expression):
    """Function call expression."""

    callee: Expression  # The function being called
    arguments: list[Expression]
    type_info: Optional[TypeInfo] = None
    mangled_name: Optional[str] = None  # Monomorphized function name

    def render_rust(self) -> str:
        # Use mangled name if available, otherwise use callee
        func_name = self.mangled_name if self.mangled_name else self.callee.render_rust()
        args = ", ".join(arg.render_rust() for arg in self.arguments)
        return f"{func_name}({args})"
