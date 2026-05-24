"""Type system for the Zinc compiler."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto


class BaseType(Enum):
    """Base types supported by Zinc."""

    INTEGER = auto()
    STRING = auto()
    BOOLEAN = auto()
    FLOAT = auto()
    CHANNEL = auto()  # Channel type (sender or receiver)
    CONTEXT = auto()  # Cancellation context
    ARRAY = auto()  # Array or Vec type
    DICT = auto()  # HashMap or BTreeMap type
    SET = auto()  # HashSet or BTreeSet type
    TUPLE = auto()  # Rust tuple type
    CALLABLE = auto()  # First-class callable values
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
        BaseType.CHANNEL: "__ZincChannel",  # Generic, element type handled separately
        BaseType.CONTEXT: "__ZincContext",
        BaseType.ARRAY: "Vec",  # Generic, element type handled separately
        BaseType.DICT: "HashMap",  # Generic, key/value handled separately
        BaseType.SET: "HashSet",  # Generic, element type handled separately
        BaseType.TUPLE: "Tuple",  # Generic, element types handled separately
        BaseType.CALLABLE: "Callable",  # Placeholder, signature handled separately
        BaseType.VOID: "()",
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
    element_tuple_info: TupleTypeInfo | None = None
    element_callable_info: CallableTypeInfo | None = None
    is_bounded: bool = False  # True if created with chan(n)

    def element_rust_type(self) -> str:
        """Generate Rust type for the channel payload."""
        if self.element_type == BaseType.TUPLE and self.element_tuple_info:
            return self.element_tuple_info.to_rust_type()
        if self.element_type == BaseType.CALLABLE and self.element_callable_info:
            return self.element_callable_info.rust_type_name()
        return type_to_rust(self.element_type)

    def to_rust_type(self) -> str:
        """Generate the shared Rust channel-wrapper type."""
        return f"__ZincChannel<{self.element_rust_type()}>"

    def to_rust_type_suffix(self) -> str:
        """Generate type suffix for mangled names (no special chars)."""
        if self.element_type == BaseType.TUPLE and self.element_tuple_info:
            elem = self.element_tuple_info.to_rust_type_suffix()
            if self.is_bounded:
                return f"BoundedChannel_{elem}"
            return f"Channel_{elem}"
        if self.element_type == BaseType.CALLABLE and self.element_callable_info:
            elem = self.element_callable_info.to_rust_type_suffix()
            if self.is_bounded:
                return f"BoundedChannel_{elem}"
            return f"Channel_{elem}"
        if self.is_bounded:
            return "BoundedChannel"
        return "Channel"


@dataclass
class ArrayTypeInfo:
    """Type information for arrays."""

    element_type: BaseType = BaseType.UNKNOWN
    element_tuple_info: TupleTypeInfo | None = None
    element_callable_info: CallableTypeInfo | None = None
    is_mutated: bool = False  # True if array is modified (push, pop, etc.)

    def element_rust_type(self) -> str:
        """Generate Rust type for the array element."""
        if self.element_type == BaseType.TUPLE and self.element_tuple_info:
            return self.element_tuple_info.to_rust_type()
        if self.element_type == BaseType.CALLABLE and self.element_callable_info:
            return self.element_callable_info.rust_type_name()
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
    key_callable_info: CallableTypeInfo | None = None
    value_callable_info: CallableTypeInfo | None = None
    kind: str = "dict"  # "dict" or "sort_dict"
    is_mutated: bool = False

    def rust_container(self) -> str:
        """Return the Rust collection type name."""
        return "BTreeMap" if self.kind == "sort_dict" else "HashMap"

    def to_rust_type(self, as_reference: bool = True) -> str:
        """Generate Rust type string."""
        if self.key_type == BaseType.CALLABLE and self.key_callable_info:
            key = self.key_callable_info.rust_type_name()
        else:
            key = type_to_rust(self.key_type)
        if self.value_type == BaseType.CALLABLE and self.value_callable_info:
            value = self.value_callable_info.rust_type_name()
        else:
            value = type_to_rust(self.value_type)
        collection_type = f"{self.rust_container()}<{key}, {value}>"
        if as_reference:
            if self.is_mutated:
                return f"&mut {collection_type}"
            return f"&{collection_type}"
        return collection_type

    def to_rust_type_suffix(self) -> str:
        """Generate type suffix for mangled names."""
        if self.key_type == BaseType.CALLABLE and self.key_callable_info:
            key = self.key_callable_info.to_rust_type_suffix()
        else:
            key = type_to_rust(self.key_type)
        if self.value_type == BaseType.CALLABLE and self.value_callable_info:
            value = self.value_callable_info.to_rust_type_suffix()
        else:
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
    element_tuple_infos: dict[int, TupleTypeInfo] = field(default_factory=dict)
    element_callable_infos: dict[int, CallableTypeInfo] = field(default_factory=dict)

    def element_rust_type(self, index: int) -> str:
        """Generate the Rust type string for an element."""
        element_type = self.element_types[index]
        if element_type == BaseType.TUPLE and index in self.element_tuple_infos:
            return self.element_tuple_infos[index].to_rust_type()
        if element_type == BaseType.CALLABLE and index in self.element_callable_infos:
            return self.element_callable_infos[index].rust_type_name()
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
        if element_type == BaseType.CALLABLE and index in self.element_callable_infos:
            return self.element_callable_infos[index].to_rust_type_suffix()
        return type_to_rust(element_type)

    def to_rust_type_suffix(self) -> str:
        """Generate type suffix for mangled names."""
        if not self.element_types:
            return "Tuple_empty"
        return "Tuple_" + "_".join(
            self.element_type_suffix(i) for i in range(len(self.element_types))
        )


@dataclass(frozen=True)
class CallableTarget:
    """A reachable callable target."""

    kind: str
    qualified_name: str
    display_name: str
    receiver_name: str | None = None
    receiver_struct_qualified_name: str | None = None
    receiver_mutability: str | None = None

    def storage_key(self) -> tuple[str, str, str | None]:
        """Return a stable key for deduping targets."""
        return (self.kind, self.qualified_name, self.receiver_name)


@dataclass
class CallableTypeInfo:
    """Type information for first-class callable values."""

    param_types: list[BaseType] = field(default_factory=list)
    param_array_infos: dict[int, ArrayTypeInfo] = field(default_factory=dict)
    param_dict_infos: dict[int, DictTypeInfo] = field(default_factory=dict)
    param_set_infos: dict[int, SetTypeInfo] = field(default_factory=dict)
    param_tuple_infos: dict[int, TupleTypeInfo] = field(default_factory=dict)
    param_callable_infos: dict[int, CallableTypeInfo] = field(default_factory=dict)
    return_type: BaseType = BaseType.UNKNOWN
    return_dict_info: DictTypeInfo | None = None
    return_set_info: SetTypeInfo | None = None
    return_tuple_info: TupleTypeInfo | None = None
    return_callable_info: CallableTypeInfo | None = None
    targets: tuple[CallableTarget, ...] = ()

    def copy(self) -> CallableTypeInfo:
        """Deep-copy callable metadata."""
        return CallableTypeInfo(
            param_types=list(self.param_types),
            param_array_infos={
                index: ArrayTypeInfo(
                    element_type=info.element_type,
                    element_tuple_info=info.element_tuple_info,
                    element_callable_info=info.element_callable_info.copy()
                    if info.element_callable_info
                    else None,
                    is_mutated=info.is_mutated,
                )
                for index, info in self.param_array_infos.items()
            },
            param_dict_infos={
                index: DictTypeInfo(
                    key_type=info.key_type,
                    value_type=info.value_type,
                    key_callable_info=info.key_callable_info.copy()
                    if info.key_callable_info
                    else None,
                    value_callable_info=info.value_callable_info.copy()
                    if info.value_callable_info
                    else None,
                    kind=info.kind,
                    is_mutated=info.is_mutated,
                )
                for index, info in self.param_dict_infos.items()
            },
            param_set_infos={
                index: SetTypeInfo(
                    element_type=info.element_type,
                    kind=info.kind,
                    is_mutated=info.is_mutated,
                )
                for index, info in self.param_set_infos.items()
            },
            param_tuple_infos={
                index: TupleTypeInfo(
                    element_types=list(info.element_types),
                    element_tuple_infos=dict(info.element_tuple_infos),
                    element_callable_infos={
                        nested_index: nested.copy()
                        for nested_index, nested in info.element_callable_infos.items()
                    },
                )
                for index, info in self.param_tuple_infos.items()
            },
            param_callable_infos={
                index: info.copy()
                for index, info in self.param_callable_infos.items()
                if info is not None
            },
            return_type=self.return_type,
            return_dict_info=DictTypeInfo(
                key_type=self.return_dict_info.key_type,
                value_type=self.return_dict_info.value_type,
                key_callable_info=self.return_dict_info.key_callable_info.copy()
                if self.return_dict_info and self.return_dict_info.key_callable_info
                else None,
                value_callable_info=self.return_dict_info.value_callable_info.copy()
                if self.return_dict_info and self.return_dict_info.value_callable_info
                else None,
                kind=self.return_dict_info.kind,
                is_mutated=self.return_dict_info.is_mutated,
            )
            if self.return_dict_info
            else None,
            return_set_info=SetTypeInfo(
                element_type=self.return_set_info.element_type,
                kind=self.return_set_info.kind,
                is_mutated=self.return_set_info.is_mutated,
            )
            if self.return_set_info
            else None,
            return_tuple_info=TupleTypeInfo(
                element_types=list(self.return_tuple_info.element_types),
                element_tuple_infos=dict(self.return_tuple_info.element_tuple_infos),
                element_callable_infos={
                    nested_index: nested.copy()
                    for nested_index, nested in self.return_tuple_info.element_callable_infos.items()
                },
            )
            if self.return_tuple_info
            else None,
            return_callable_info=self.return_callable_info.copy()
            if self.return_callable_info
            else None,
            targets=tuple(self.targets),
        )

    def structural_key(self) -> tuple:
        """Return a stable signature key that ignores concrete target identity."""
        return (
            tuple(self._param_key(index, base_type) for index, base_type in enumerate(self.param_types)),
            self._value_key(
                self.return_type,
                dict_info=self.return_dict_info,
                set_info=self.return_set_info,
                tuple_info=self.return_tuple_info,
                callable_info=self.return_callable_info,
            ),
        )

    def with_target(self, target: CallableTarget) -> CallableTypeInfo:
        """Return a copy with an additional target if needed."""
        if any(existing.storage_key() == target.storage_key() for existing in self.targets):
            return self.copy()
        copied = self.copy()
        copied.targets = (*copied.targets, target)
        return copied

    def merge_targets_from(self, other: CallableTypeInfo) -> CallableTypeInfo:
        """Merge target identity into an otherwise-compatible callable signature."""
        if self.structural_key() != other.structural_key():
            raise ValueError("cannot merge callable infos with different structural signatures")
        merged = self.copy()
        seen = {target.storage_key() for target in merged.targets}
        for target in other.targets:
            if target.storage_key() not in seen:
                merged.targets = (*merged.targets, target)
                seen.add(target.storage_key())
        return merged

    def rust_type_name(self) -> str:
        """Return the generated Rust enum name for this signature."""
        return f"__ZincCallable_{self.to_rust_type_suffix()}"

    def to_rust_type_suffix(self) -> str:
        """Return a Rust-safe suffix describing this callable signature."""
        params = [self._param_suffix(index, base_type) for index, base_type in enumerate(self.param_types)]
        if not params:
            params_part = "Unit"
        else:
            params_part = "_".join(params)
        return_part = self._value_suffix(
            self.return_type,
            dict_info=self.return_dict_info,
            set_info=self.return_set_info,
            tuple_info=self.return_tuple_info,
            callable_info=self.return_callable_info,
        )
        return f"{params_part}_to_{return_part}"

    def _param_key(self, index: int, base_type: BaseType) -> tuple:
        return self._value_key(
            base_type,
            array_info=self.param_array_infos.get(index),
            dict_info=self.param_dict_infos.get(index),
            set_info=self.param_set_infos.get(index),
            tuple_info=self.param_tuple_infos.get(index),
            callable_info=self.param_callable_infos.get(index),
        )

    def _value_key(
        self,
        base_type: BaseType,
        *,
        array_info: ArrayTypeInfo | None = None,
        dict_info: DictTypeInfo | None = None,
        set_info: SetTypeInfo | None = None,
        tuple_info: TupleTypeInfo | None = None,
        callable_info: CallableTypeInfo | None = None,
    ) -> tuple:
        if base_type == BaseType.ARRAY and array_info:
            return ("array", array_info.to_rust_type_suffix())
        if base_type == BaseType.DICT and dict_info:
            return ("dict", dict_info.to_rust_type_suffix())
        if base_type == BaseType.SET and set_info:
            return ("set", set_info.to_rust_type_suffix())
        if base_type == BaseType.TUPLE and tuple_info:
            return ("tuple", tuple_info.to_rust_type_suffix())
        if base_type == BaseType.CALLABLE and callable_info:
            return ("callable", callable_info.to_rust_type_suffix())
        if base_type == BaseType.VOID:
            return ("unit",)
        return (base_type.name.lower(),)

    def _param_suffix(self, index: int, base_type: BaseType) -> str:
        return self._value_suffix(
            base_type,
            array_info=self.param_array_infos.get(index),
            dict_info=self.param_dict_infos.get(index),
            set_info=self.param_set_infos.get(index),
            tuple_info=self.param_tuple_infos.get(index),
            callable_info=self.param_callable_infos.get(index),
        )

    def _value_suffix(
        self,
        base_type: BaseType,
        *,
        array_info: ArrayTypeInfo | None = None,
        dict_info: DictTypeInfo | None = None,
        set_info: SetTypeInfo | None = None,
        tuple_info: TupleTypeInfo | None = None,
        callable_info: CallableTypeInfo | None = None,
    ) -> str:
        if base_type == BaseType.ARRAY and array_info:
            return array_info.to_rust_type_suffix()
        if base_type == BaseType.DICT and dict_info:
            return dict_info.to_rust_type_suffix()
        if base_type == BaseType.SET and set_info:
            return set_info.to_rust_type_suffix()
        if base_type == BaseType.TUPLE and tuple_info:
            return tuple_info.to_rust_type_suffix()
        if base_type == BaseType.CALLABLE and callable_info:
            return callable_info.to_rust_type_suffix()
        if base_type == BaseType.VOID:
            return "Unit"
        if base_type == BaseType.CONTEXT:
            return "Context"
        return type_to_rust(base_type)


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
