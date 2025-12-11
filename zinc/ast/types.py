"""Type system for the Zinc compiler."""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional


class BaseType(Enum):
    """Base types supported by Zinc."""

    INTEGER = auto()
    STRING = auto()
    BOOLEAN = auto()
    FLOAT = auto()
    CHANNEL = auto()  # Channel type (sender or receiver)
    ARRAY = auto()  # Array or Vec type
    UNKNOWN = auto()  # For unresolved types

    def __repr__(self):
        return self.name


class TypeInfo:
    """Rich type information with promotion support."""

    def __init__(self, base: BaseType):
        self.base = base

    def __eq__(self, other):
        if isinstance(other, TypeInfo):
            return self.base == other.base
        return False

    def __repr__(self):
        return f"TypeInfo({self.base})"

    @staticmethod
    def promote(left: "TypeInfo", right: "TypeInfo") -> "TypeInfo":
        """Determine result type for binary operation.

        Type promotion rules:
        - int + int -> int
        - float + float -> float
        - int + float -> float (promote int to float)
        """
        if left.base == right.base:
            return TypeInfo(left.base)

        # int + float -> float
        if {left.base, right.base} == {BaseType.INTEGER, BaseType.FLOAT}:
            return TypeInfo(BaseType.FLOAT)

        # Default: unknown (should trigger error in validation phase)
        return TypeInfo(BaseType.UNKNOWN)


def parse_literal(literal_text: str) -> BaseType:
    """Parse a literal string and return its type."""
    # Handle negative numbers
    text = literal_text.lstrip("-")

    if text.isdigit():
        return BaseType.INTEGER
    elif text.replace(".", "", 1).isdigit() and text.count(".") < 2:
        return BaseType.FLOAT
    elif literal_text.startswith('"') and literal_text.endswith('"'):
        return BaseType.STRING
    elif literal_text in ("true", "false"):
        return BaseType.BOOLEAN
    else:
        raise ValueError(f"Unknown literal type: {literal_text}")


def type_to_rust(base_type: BaseType) -> str:
    """Convert a BaseType to its Rust type name."""
    mapping = {
        BaseType.INTEGER: "i64",
        BaseType.FLOAT: "f64",
        BaseType.STRING: "String",
        BaseType.BOOLEAN: "bool",
        BaseType.CHANNEL: "chan",  # Placeholder for mangled names
        BaseType.ARRAY: "Vec",  # Generic, element type handled separately
        BaseType.UNKNOWN: "unknown",
    }
    return mapping.get(base_type, "unknown")


@dataclass
class ChannelTypeInfo:
    """Type information for channel types."""

    element_type: BaseType = BaseType.UNKNOWN  # Type of values sent/received
    is_bounded: bool = False  # True if created with chan(n)

    def to_rust_sender(self) -> str:
        """Generate Rust sender type."""
        elem = type_to_rust(self.element_type)
        if self.is_bounded:
            return f"tokio::sync::mpsc::Sender<{elem}>"
        return f"tokio::sync::mpsc::UnboundedSender<{elem}>"

    def to_rust_receiver(self) -> str:
        """Generate Rust receiver type."""
        elem = type_to_rust(self.element_type)
        if self.is_bounded:
            return f"tokio::sync::mpsc::Receiver<{elem}>"
        return f"tokio::sync::mpsc::UnboundedReceiver<{elem}>"

    def to_rust_type_suffix(self) -> str:
        """Generate type suffix for mangled names (no special chars)."""
        elem = type_to_rust(self.element_type)
        if self.is_bounded:
            return f"Sender{elem}"
        return f"UnboundedSender{elem}"


@dataclass
class ArrayTypeInfo:
    """Type information for arrays."""

    element_type: BaseType = BaseType.UNKNOWN
    is_vector: bool = False  # True if .push() was called

    def to_rust_type(self) -> str:
        """Generate Rust type string."""
        elem = type_to_rust(self.element_type)
        if self.is_vector:
            return f"Vec<{elem}>"
        return f"[{elem}]"
