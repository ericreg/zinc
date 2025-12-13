"""Expression AST nodes for the Zinc compiler."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from .types import BaseType, TypeInfo, ChannelTypeInfo, ArrayTypeInfo, type_to_rust


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
        # Handle format string interpolation like "{self.a}" or "{var}"
        if self.type_info and self.type_info.base == BaseType.STRING:
            import re
            interpolations = re.findall(r"\{([^}]+)\}", self.value)
            if interpolations:
                # Convert to format!() macro
                format_string = re.sub(r"\{[^}]+\}", "{}", self.value)
                args = ", ".join(interpolations)
                return f"format!({format_string}, {args})"
        return self.value

    def render_rust_as_string(self) -> str:
        """Render as an owned String (for struct fields expecting String type)."""
        import re
        # Check for format string interpolation
        interpolations = re.findall(r"\{([^}]+)\}", self.value)
        if interpolations:
            format_string = re.sub(r"\{[^}]+\}", "{}", self.value)
            args = ", ".join(interpolations)
            return f"format!({format_string}, {args})"
        # Wrap with String::from()
        return f"String::from({self.value})"


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


@dataclass
class ChannelCreateExpr(Expression):
    """Channel creation expression: chan() or chan(n)."""

    capacity: Optional[Expression] = None  # None = unbounded, else bounded
    type_info: Optional[TypeInfo] = None
    channel_info: Optional[ChannelTypeInfo] = None  # Element type info

    def render_rust(self) -> str:
        if self.channel_info is None:
            raise ValueError("Channel element type not inferred")

        elem = type_to_rust(self.channel_info.element_type)

        if self.capacity is None:
            return f"tokio::sync::mpsc::unbounded_channel::<{elem}>()"
        else:
            cap = self.capacity.render_rust()
            return f"tokio::sync::mpsc::channel::<{elem}>({cap})"


@dataclass
class ChannelReceiveExpr(Expression):
    """Channel receive expression: <- receiver."""

    channel: Expression  # Must resolve to a receiver
    type_info: Optional[TypeInfo] = None  # Type of received value

    def render_rust(self) -> str:
        chan = self.channel.render_rust()
        # Use unwrap() to panic on closed channel
        return f"{chan}.recv().await.unwrap()"


@dataclass
class ArrayLiteralExpr(Expression):
    """Array literal: [1, 2, 3] or []."""

    elements: list[Expression]
    array_info: Optional[ArrayTypeInfo] = None
    type_info: Optional[TypeInfo] = None

    def render_rust(self) -> str:
        if self.array_info and self.array_info.is_vector:
            if not self.elements:
                # Empty Vec - type annotation added at declaration level
                return "Vec::new()"
            elems = ", ".join(e.render_rust() for e in self.elements)
            return f"vec![{elems}]"
        else:
            elems = ", ".join(e.render_rust() for e in self.elements)
            return f"[{elems}]"


@dataclass
class IndexExpr(Expression):
    """Index access: a[0]."""

    target: Expression
    index: Expression
    type_info: Optional[TypeInfo] = None

    def render_rust(self) -> str:
        return f"{self.target.render_rust()}[{self.index.render_rust()}]"


@dataclass
class MethodCallExpr(Expression):
    """Method call: obj.method(args)."""

    target: Expression
    method_name: str
    arguments: list[Expression]
    type_info: Optional[TypeInfo] = None
    is_static: bool = False  # True if calling a static method

    def render_rust(self) -> str:
        args = ", ".join(arg.render_rust() for arg in self.arguments)
        # Static method call on self should use Self::method() syntax
        if self.is_static:
            return f"Self::{self.method_name}({args})"
        return f"{self.target.render_rust()}.{self.method_name}({args})"


@dataclass
class RangeExpr(Expression):
    """Range expression: 0..10 or 0..=10."""

    start: Expression
    end: Expression
    inclusive: bool = False  # True for ..=
    type_info: Optional[TypeInfo] = None

    def render_rust(self) -> str:
        op = "..=" if self.inclusive else ".."
        return f"{self.start.render_rust()}{op}{self.end.render_rust()}"
