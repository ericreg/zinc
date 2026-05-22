"""Type system for the Zinc compiler."""

from dataclasses import dataclass, field
from enum import Enum, auto


class BaseType(Enum):
    """Base types supported by Zinc."""

    INTEGER = auto()
    STRING = auto()
    BOOLEAN = auto()
    FLOAT = auto()
    CHANNEL = auto()  # Channel type (sender or receiver)
    ARRAY = auto()  # Array or Vec type
    DICT = auto()  # HashMap or BTreeMap type
    SET = auto()  # HashSet or BTreeSet type
    TUPLE = auto()  # Rust tuple type
    STRUCT = auto()  # Struct type
    VOID = auto()  # For functions with no return value
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
        BaseType.DICT: "HashMap",  # Generic, key/value handled separately
        BaseType.SET: "HashSet",  # Generic, element type handled separately
        BaseType.TUPLE: "Tuple",  # Generic, element types handled separately
        BaseType.UNKNOWN: "unknown",
    }
    return mapping.get(base_type, "unknown")


def promote_numeric(left: BaseType, right: BaseType) -> BaseType:
    """Promote matching primitive types, allowing int/float -> float."""
    if left == BaseType.UNKNOWN:
        return right
    if right == BaseType.UNKNOWN:
        return left
    if left == right:
        return left
    if {left, right} == {BaseType.INTEGER, BaseType.FLOAT}:
        return BaseType.FLOAT
    return BaseType.UNKNOWN


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
        if self.is_bounded:
            return "Sender"
        return "UnboundedSender"


@dataclass
class ArrayTypeInfo:
    """Type information for arrays."""

    element_type: BaseType = BaseType.UNKNOWN
    element_tuple_info: "TupleTypeInfo | None" = None
    is_mutated: bool = False  # True if array is modified (push, pop, etc.)

    def element_rust_type(self) -> str:
        """Generate Rust type for the array element."""
        if self.element_type == BaseType.TUPLE and self.element_tuple_info:
            return self.element_tuple_info.to_rust_type()
        return type_to_rust(self.element_type)

    def to_rust_type(self, as_reference: bool = True) -> str:
        """Generate Rust type string (always Vec in Zinc).

        Args:
            as_reference: If True, generate &Vec<T> or &mut Vec<T> for parameters
        """
        elem = self.element_rust_type()
        if as_reference:
            if self.is_mutated:
                return f"&mut Vec<{elem}>"
            return f"&Vec<{elem}>"
        return f"Vec<{elem}>"

    def to_rust_type_suffix(self) -> str:
        """Generate type suffix for mangled names."""
        if self.element_type == BaseType.TUPLE and self.element_tuple_info:
            elem = self.element_tuple_info.to_rust_type_suffix()
        else:
            elem = type_to_rust(self.element_type)
        return f"Vec_{elem}"


@dataclass
class DictTypeInfo:
    """Type information for dict/sort_dict containers."""

    key_type: BaseType = BaseType.UNKNOWN
    value_type: BaseType = BaseType.UNKNOWN
    kind: str = "dict"  # "dict" or "sort_dict"
    is_mutated: bool = False

    def rust_container(self) -> str:
        """Return the Rust collection type name."""
        return "BTreeMap" if self.kind == "sort_dict" else "HashMap"

    def to_rust_type(self, as_reference: bool = True) -> str:
        """Generate Rust type string."""
        key = type_to_rust(self.key_type)
        value = type_to_rust(self.value_type)
        collection_type = f"{self.rust_container()}<{key}, {value}>"
        if as_reference:
            if self.is_mutated:
                return f"&mut {collection_type}"
            return f"&{collection_type}"
        return collection_type

    def to_rust_type_suffix(self) -> str:
        """Generate type suffix for mangled names."""
        key = type_to_rust(self.key_type)
        value = type_to_rust(self.value_type)
        return f"{self.rust_container()}_{key}_{value}"


@dataclass
class SetTypeInfo:
    """Type information for set/sort_set containers."""

    element_type: BaseType = BaseType.UNKNOWN
    kind: str = "set"  # "set" or "sort_set"
    is_mutated: bool = False

    def rust_container(self) -> str:
        """Return the Rust collection type name."""
        return "BTreeSet" if self.kind == "sort_set" else "HashSet"

    def to_rust_type(self, as_reference: bool = True) -> str:
        """Generate Rust type string."""
        elem = type_to_rust(self.element_type)
        collection_type = f"{self.rust_container()}<{elem}>"
        if as_reference:
            if self.is_mutated:
                return f"&mut {collection_type}"
            return f"&{collection_type}"
        return collection_type

    def to_rust_type_suffix(self) -> str:
        """Generate type suffix for mangled names."""
        elem = type_to_rust(self.element_type)
        return f"{self.rust_container()}_{elem}"


@dataclass
class TupleTypeInfo:
    """Type information for tuple values."""

    element_types: list[BaseType] = field(default_factory=list)
    element_tuple_infos: dict[int, "TupleTypeInfo"] = field(default_factory=dict)

    def element_rust_type(self, index: int) -> str:
        """Generate the Rust type string for an element."""
        element_type = self.element_types[index]
        if element_type == BaseType.TUPLE and index in self.element_tuple_infos:
            return self.element_tuple_infos[index].to_rust_type()
        return type_to_rust(element_type)

    def to_rust_type(self) -> str:
        """Generate Rust tuple type syntax."""
        elements = [self.element_rust_type(i) for i in range(len(self.element_types))]
        if len(elements) == 1:
            return f"({elements[0]},)"
        return f"({', '.join(elements)})"

    def element_type_suffix(self, index: int) -> str:
        """Generate a mangling suffix for an element."""
        element_type = self.element_types[index]
        if element_type == BaseType.TUPLE and index in self.element_tuple_infos:
            return self.element_tuple_infos[index].to_rust_type_suffix()
        return type_to_rust(element_type)

    def to_rust_type_suffix(self) -> str:
        """Generate type suffix for mangled names."""
        if not self.element_types:
            return "Tuple_empty"
        return "Tuple_" + "_".join(
            self.element_type_suffix(i) for i in range(len(self.element_types))
        )


# Registry of mutating methods by type
# Maps BaseType -> set of method names that mutate the receiver
MUTATING_METHODS: dict[BaseType, set[str]] = {
    BaseType.ARRAY: {"push", "pop", "remove", "insert", "clear", "sort", "reverse"},
    BaseType.DICT: {"insert", "remove", "clear"},
    BaseType.SET: {"push", "insert", "remove", "clear"},
}


def is_mutating_method(receiver_type: BaseType, method_name: str) -> bool:
    """Check if a method call mutates the receiver."""
    methods = MUTATING_METHODS.get(receiver_type, set())
    return method_name in methods
