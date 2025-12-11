"""Type system for the Zinc compiler."""

from enum import Enum, auto
from typing import Optional


class BaseType(Enum):
    """Base types supported by Zinc."""

    INTEGER = auto()
    STRING = auto()
    BOOLEAN = auto()
    FLOAT = auto()
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
