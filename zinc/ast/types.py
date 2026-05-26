"""Type system for the Zinc compiler."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto

from zinc.string_literals import is_string_literal


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
    NEVER = auto()  # Diverging control flow that never completes normally
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
    elif is_string_literal(literal_text):
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
        BaseType.STRUCT: "Struct",
        BaseType.VOID: "()",
        BaseType.NEVER: "!",
        BaseType.UNKNOWN: "unknown",
    }
    return mapping.get(base_type, "unknown")


def _sanitize_type_fragment(text: str) -> str:
    """Convert a type/signature fragment into a Rust-safe identifier chunk."""
    cleaned = []
    for char in text:
        if char.isalnum():
            cleaned.append(char)
        else:
            cleaned.append("_")
    return "".join(cleaned).strip("_") or "empty"


def _named_struct_suffix(qualified_name: str | None) -> str:
    """Return a stable suffix fragment for a named struct identity."""
    if not qualified_name:
        return "Struct_unknown"
    return f"Struct_{_sanitize_type_fragment(qualified_name)}"


def _named_struct_rust_name(qualified_name: str | None) -> str:
    """Return a best-effort Rust type name for a named struct."""
    if not qualified_name:
        return "unknown"
    return qualified_name.rpartition("::")[2] or qualified_name


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
class AnonymousStructFieldInfo:
    """Type information for a single anonymous struct field."""

    name: str
    resolved_type: BaseType = BaseType.UNKNOWN
    array_info: ArrayTypeInfo | None = None
    dict_info: DictTypeInfo | None = None
    set_info: SetTypeInfo | None = None
    tuple_info: TupleTypeInfo | None = None
    callable_info: CallableTypeInfo | None = None
    struct_qualified_name: str | None = None
    anonymous_struct_info: AnonymousStructTypeInfo | None = None

    def copy(self) -> AnonymousStructFieldInfo:
        """Deep-copy field metadata."""
        return AnonymousStructFieldInfo(
            name=self.name,
            resolved_type=self.resolved_type,
            array_info=self.array_info.copy() if self.array_info else None,
            dict_info=self.dict_info.copy() if self.dict_info else None,
            set_info=self.set_info.copy() if self.set_info else None,
            tuple_info=self.tuple_info.copy() if self.tuple_info else None,
            callable_info=self.callable_info.copy() if self.callable_info else None,
            struct_qualified_name=self.struct_qualified_name,
            anonymous_struct_info=self.anonymous_struct_info.copy() if self.anonymous_struct_info else None,
        )

    def structural_key(self) -> tuple[str, tuple]:
        """Return a stable structural key for this field."""
        return (
            self.name,
            value_type_key(
                self.resolved_type,
                array_info=self.array_info,
                dict_info=self.dict_info,
                set_info=self.set_info,
                tuple_info=self.tuple_info,
                callable_info=self.callable_info,
                struct_qualified_name=self.struct_qualified_name,
                anonymous_struct_info=self.anonymous_struct_info,
            ),
        )

    def rust_type_suffix(self) -> str:
        """Return a Rust-safe suffix fragment for this field type."""
        return value_type_suffix(
            self.resolved_type,
            array_info=self.array_info,
            dict_info=self.dict_info,
            set_info=self.set_info,
            tuple_info=self.tuple_info,
            callable_info=self.callable_info,
            struct_qualified_name=self.struct_qualified_name,
            anonymous_struct_info=self.anonymous_struct_info,
        )


@dataclass
class AnonymousStructTypeInfo:
    """Type information for anonymous structs."""

    fields: list[AnonymousStructFieldInfo] = field(default_factory=list)

    def copy(self) -> AnonymousStructTypeInfo:
        """Deep-copy anonymous struct metadata."""
        return AnonymousStructTypeInfo(fields=[field.copy() for field in self.fields])

    def field_map(self) -> dict[str, AnonymousStructFieldInfo]:
        """Return fields indexed by name."""
        return {field.name: field for field in self.fields}

    def get_field(self, name: str) -> AnonymousStructFieldInfo | None:
        """Return the field with this name, if present."""
        for field in self.fields:
            if field.name == name:
                return field
        return None

    def canonical_fields(self) -> list[AnonymousStructFieldInfo]:
        """Return fields sorted by name for structural comparisons."""
        return sorted(self.fields, key=lambda field: field.name)

    def structural_key(self) -> tuple:
        """Return a stable key that ignores field declaration order."""
        return tuple(field.structural_key() for field in self.canonical_fields())

    def to_rust_type_suffix(self) -> str:
        """Return a Rust-safe suffix describing this anonymous struct shape."""
        if not self.fields:
            return "AnonStruct_empty"
        parts = [
            f"{_sanitize_type_fragment(field.name)}_{field.rust_type_suffix()}"
            for field in self.canonical_fields()
        ]
        return "AnonStruct_" + "_".join(parts)

    def rust_type_name(self) -> str:
        """Return the synthesized Rust type name for this shape."""
        return f"__ZincAnonStruct_{self.to_rust_type_suffix()}"


@dataclass
class ChannelTypeInfo:
    """Type information for channel types."""

    element_type: BaseType = BaseType.UNKNOWN  # Type of values sent/received
    element_tuple_info: TupleTypeInfo | None = None
    element_callable_info: CallableTypeInfo | None = None
    element_struct_qualified_name: str | None = None
    element_anonymous_struct_info: AnonymousStructTypeInfo | None = None
    is_bounded: bool = False  # True if created with chan(n)

    def element_rust_type(self) -> str:
        """Generate Rust type for the channel payload."""
        if self.element_type == BaseType.TUPLE and self.element_tuple_info:
            return self.element_tuple_info.to_rust_type()
        if self.element_type == BaseType.CALLABLE and self.element_callable_info:
            return self.element_callable_info.rust_type_name()
        if self.element_type == BaseType.STRUCT:
            if self.element_anonymous_struct_info:
                return self.element_anonymous_struct_info.rust_type_name()
            return _named_struct_rust_name(self.element_struct_qualified_name)
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
        if self.element_type == BaseType.STRUCT:
            elem = value_type_suffix(
                BaseType.STRUCT,
                struct_qualified_name=self.element_struct_qualified_name,
                anonymous_struct_info=self.element_anonymous_struct_info,
            )
            if self.is_bounded:
                return f"BoundedChannel_{elem}"
            return f"Channel_{elem}"
        if self.is_bounded:
            return "BoundedChannel"
        return "Channel"

    def copy(self) -> ChannelTypeInfo:
        """Deep-copy channel metadata."""
        return ChannelTypeInfo(
            element_type=self.element_type,
            element_tuple_info=self.element_tuple_info.copy() if self.element_tuple_info else None,
            element_callable_info=self.element_callable_info.copy() if self.element_callable_info else None,
            element_struct_qualified_name=self.element_struct_qualified_name,
            element_anonymous_struct_info=self.element_anonymous_struct_info.copy()
            if self.element_anonymous_struct_info
            else None,
            is_bounded=self.is_bounded,
        )


@dataclass
class ArrayTypeInfo:
    """Type information for arrays."""

    element_type: BaseType = BaseType.UNKNOWN
    element_tuple_info: TupleTypeInfo | None = None
    element_callable_info: CallableTypeInfo | None = None
    element_struct_qualified_name: str | None = None
    element_anonymous_struct_info: AnonymousStructTypeInfo | None = None
    is_mutated: bool = False  # True if array is modified (push, pop, etc.)

    def element_rust_type(self) -> str:
        """Generate Rust type for the array element."""
        if self.element_type == BaseType.TUPLE and self.element_tuple_info:
            return self.element_tuple_info.to_rust_type()
        if self.element_type == BaseType.CALLABLE and self.element_callable_info:
            return self.element_callable_info.rust_type_name()
        if self.element_type == BaseType.STRUCT:
            if self.element_anonymous_struct_info:
                return self.element_anonymous_struct_info.rust_type_name()
            return _named_struct_rust_name(self.element_struct_qualified_name)
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
        elif self.element_type == BaseType.STRUCT:
            elem = value_type_suffix(
                BaseType.STRUCT,
                struct_qualified_name=self.element_struct_qualified_name,
                anonymous_struct_info=self.element_anonymous_struct_info,
            )
        else:
            elem = type_to_rust(self.element_type)
        return f"Vec_{elem}"

    def copy(self) -> ArrayTypeInfo:
        """Deep-copy array metadata."""
        return ArrayTypeInfo(
            element_type=self.element_type,
            element_tuple_info=self.element_tuple_info.copy() if self.element_tuple_info else None,
            element_callable_info=self.element_callable_info.copy() if self.element_callable_info else None,
            element_struct_qualified_name=self.element_struct_qualified_name,
            element_anonymous_struct_info=self.element_anonymous_struct_info.copy()
            if self.element_anonymous_struct_info
            else None,
            is_mutated=self.is_mutated,
        )


@dataclass
class DictTypeInfo:
    """Type information for dict/sort_dict containers."""

    key_type: BaseType = BaseType.UNKNOWN
    value_type: BaseType = BaseType.UNKNOWN
    key_callable_info: CallableTypeInfo | None = None
    value_callable_info: CallableTypeInfo | None = None
    key_struct_qualified_name: str | None = None
    value_struct_qualified_name: str | None = None
    key_anonymous_struct_info: AnonymousStructTypeInfo | None = None
    value_anonymous_struct_info: AnonymousStructTypeInfo | None = None
    kind: str = "dict"  # "dict" or "sort_dict"
    is_mutated: bool = False

    def rust_container(self) -> str:
        """Return the Rust collection type name."""
        return "BTreeMap" if self.kind == "sort_dict" else "HashMap"

    def to_rust_type(self, as_reference: bool = True) -> str:
        """Generate Rust type string."""
        if self.key_type == BaseType.CALLABLE and self.key_callable_info:
            key = self.key_callable_info.rust_type_name()
        elif self.key_type == BaseType.STRUCT:
            if self.key_anonymous_struct_info:
                key = self.key_anonymous_struct_info.rust_type_name()
            else:
                key = _named_struct_rust_name(self.key_struct_qualified_name)
        else:
            key = type_to_rust(self.key_type)
        if self.value_type == BaseType.CALLABLE and self.value_callable_info:
            value = self.value_callable_info.rust_type_name()
        elif self.value_type == BaseType.STRUCT:
            if self.value_anonymous_struct_info:
                value = self.value_anonymous_struct_info.rust_type_name()
            else:
                value = _named_struct_rust_name(self.value_struct_qualified_name)
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
        elif self.key_type == BaseType.STRUCT:
            key = value_type_suffix(
                BaseType.STRUCT,
                struct_qualified_name=self.key_struct_qualified_name,
                anonymous_struct_info=self.key_anonymous_struct_info,
            )
        else:
            key = type_to_rust(self.key_type)
        if self.value_type == BaseType.CALLABLE and self.value_callable_info:
            value = self.value_callable_info.to_rust_type_suffix()
        elif self.value_type == BaseType.STRUCT:
            value = value_type_suffix(
                BaseType.STRUCT,
                struct_qualified_name=self.value_struct_qualified_name,
                anonymous_struct_info=self.value_anonymous_struct_info,
            )
        else:
            value = type_to_rust(self.value_type)
        return f"{self.rust_container()}_{key}_{value}"

    def copy(self) -> DictTypeInfo:
        """Deep-copy dict metadata."""
        return DictTypeInfo(
            key_type=self.key_type,
            value_type=self.value_type,
            key_callable_info=self.key_callable_info.copy() if self.key_callable_info else None,
            value_callable_info=self.value_callable_info.copy() if self.value_callable_info else None,
            key_struct_qualified_name=self.key_struct_qualified_name,
            value_struct_qualified_name=self.value_struct_qualified_name,
            key_anonymous_struct_info=self.key_anonymous_struct_info.copy() if self.key_anonymous_struct_info else None,
            value_anonymous_struct_info=self.value_anonymous_struct_info.copy()
            if self.value_anonymous_struct_info
            else None,
            kind=self.kind,
            is_mutated=self.is_mutated,
        )


@dataclass
class SetTypeInfo:
    """Type information for set/sort_set containers."""

    element_type: BaseType = BaseType.UNKNOWN
    element_struct_qualified_name: str | None = None
    element_anonymous_struct_info: AnonymousStructTypeInfo | None = None
    kind: str = "set"  # "set" or "sort_set"
    is_mutated: bool = False

    def rust_container(self) -> str:
        """Return the Rust collection type name."""
        return "BTreeSet" if self.kind == "sort_set" else "HashSet"

    def to_rust_type(self, as_reference: bool = True) -> str:
        """Generate Rust type string."""
        if self.element_type == BaseType.STRUCT:
            if self.element_anonymous_struct_info:
                elem = self.element_anonymous_struct_info.rust_type_name()
            else:
                elem = _named_struct_rust_name(self.element_struct_qualified_name)
        else:
            elem = type_to_rust(self.element_type)
        collection_type = f"{self.rust_container()}<{elem}>"
        if as_reference:
            if self.is_mutated:
                return f"&mut {collection_type}"
            return f"&{collection_type}"
        return collection_type

    def to_rust_type_suffix(self) -> str:
        """Generate type suffix for mangled names."""
        if self.element_type == BaseType.STRUCT:
            elem = value_type_suffix(
                BaseType.STRUCT,
                struct_qualified_name=self.element_struct_qualified_name,
                anonymous_struct_info=self.element_anonymous_struct_info,
            )
        else:
            elem = type_to_rust(self.element_type)
        return f"{self.rust_container()}_{elem}"

    def copy(self) -> SetTypeInfo:
        """Deep-copy set metadata."""
        return SetTypeInfo(
            element_type=self.element_type,
            element_struct_qualified_name=self.element_struct_qualified_name,
            element_anonymous_struct_info=self.element_anonymous_struct_info.copy()
            if self.element_anonymous_struct_info
            else None,
            kind=self.kind,
            is_mutated=self.is_mutated,
        )


@dataclass
class TupleTypeInfo:
    """Type information for tuple values."""

    element_types: list[BaseType] = field(default_factory=list)
    element_tuple_infos: dict[int, TupleTypeInfo] = field(default_factory=dict)
    element_callable_infos: dict[int, CallableTypeInfo] = field(default_factory=dict)
    element_struct_qualified_names: dict[int, str] = field(default_factory=dict)
    element_anonymous_struct_infos: dict[int, AnonymousStructTypeInfo] = field(default_factory=dict)

    def element_rust_type(self, index: int) -> str:
        """Generate the Rust type string for an element."""
        element_type = self.element_types[index]
        if element_type == BaseType.TUPLE and index in self.element_tuple_infos:
            return self.element_tuple_infos[index].to_rust_type()
        if element_type == BaseType.CALLABLE and index in self.element_callable_infos:
            return self.element_callable_infos[index].rust_type_name()
        if element_type == BaseType.STRUCT:
            if index in self.element_anonymous_struct_infos:
                return self.element_anonymous_struct_infos[index].rust_type_name()
            return _named_struct_rust_name(self.element_struct_qualified_names.get(index))
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
        if element_type == BaseType.STRUCT:
            return value_type_suffix(
                BaseType.STRUCT,
                struct_qualified_name=self.element_struct_qualified_names.get(index),
                anonymous_struct_info=self.element_anonymous_struct_infos.get(index),
            )
        return type_to_rust(element_type)

    def to_rust_type_suffix(self) -> str:
        """Generate type suffix for mangled names."""
        if not self.element_types:
            return "Tuple_empty"
        return "Tuple_" + "_".join(
            self.element_type_suffix(i) for i in range(len(self.element_types))
        )

    def copy(self) -> TupleTypeInfo:
        """Deep-copy tuple metadata."""
        return TupleTypeInfo(
            element_types=list(self.element_types),
            element_tuple_infos={
                index: info.copy()
                for index, info in self.element_tuple_infos.items()
            },
            element_callable_infos={
                index: info.copy()
                for index, info in self.element_callable_infos.items()
            },
            element_struct_qualified_names=dict(self.element_struct_qualified_names),
            element_anonymous_struct_infos={
                index: info.copy()
                for index, info in self.element_anonymous_struct_infos.items()
            },
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
    param_struct_qualified_names: dict[int, str] = field(default_factory=dict)
    param_anonymous_struct_infos: dict[int, AnonymousStructTypeInfo] = field(default_factory=dict)
    return_type: BaseType = BaseType.UNKNOWN
    return_dict_info: DictTypeInfo | None = None
    return_set_info: SetTypeInfo | None = None
    return_tuple_info: TupleTypeInfo | None = None
    return_callable_info: CallableTypeInfo | None = None
    return_struct_qualified_name: str | None = None
    return_anonymous_struct_info: AnonymousStructTypeInfo | None = None
    targets: tuple[CallableTarget, ...] = ()

    def copy(self) -> CallableTypeInfo:
        """Deep-copy callable metadata."""
        return CallableTypeInfo(
            param_types=list(self.param_types),
            param_array_infos={
                index: info.copy()
                for index, info in self.param_array_infos.items()
            },
            param_dict_infos={
                index: info.copy()
                for index, info in self.param_dict_infos.items()
            },
            param_set_infos={
                index: info.copy()
                for index, info in self.param_set_infos.items()
            },
            param_tuple_infos={
                index: info.copy()
                for index, info in self.param_tuple_infos.items()
            },
            param_callable_infos={
                index: info.copy()
                for index, info in self.param_callable_infos.items()
                if info is not None
            },
            param_struct_qualified_names=dict(self.param_struct_qualified_names),
            param_anonymous_struct_infos={
                index: info.copy()
                for index, info in self.param_anonymous_struct_infos.items()
            },
            return_type=self.return_type,
            return_dict_info=self.return_dict_info.copy() if self.return_dict_info else None,
            return_set_info=self.return_set_info.copy() if self.return_set_info else None,
            return_tuple_info=self.return_tuple_info.copy() if self.return_tuple_info else None,
            return_callable_info=self.return_callable_info.copy()
            if self.return_callable_info
            else None,
            return_struct_qualified_name=self.return_struct_qualified_name,
            return_anonymous_struct_info=self.return_anonymous_struct_info.copy()
            if self.return_anonymous_struct_info
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
                struct_qualified_name=self.return_struct_qualified_name,
                anonymous_struct_info=self.return_anonymous_struct_info,
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
            struct_qualified_name=self.param_struct_qualified_names.get(index),
            anonymous_struct_info=self.param_anonymous_struct_infos.get(index),
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
        struct_qualified_name: str | None = None,
        anonymous_struct_info: AnonymousStructTypeInfo | None = None,
    ) -> tuple:
        return value_type_key(
            base_type,
            array_info=array_info,
            dict_info=dict_info,
            set_info=set_info,
            tuple_info=tuple_info,
            callable_info=callable_info,
            struct_qualified_name=struct_qualified_name,
            anonymous_struct_info=anonymous_struct_info,
        )

    def _param_suffix(self, index: int, base_type: BaseType) -> str:
        return self._value_suffix(
            base_type,
            array_info=self.param_array_infos.get(index),
            dict_info=self.param_dict_infos.get(index),
            set_info=self.param_set_infos.get(index),
            tuple_info=self.param_tuple_infos.get(index),
            callable_info=self.param_callable_infos.get(index),
            struct_qualified_name=self.param_struct_qualified_names.get(index),
            anonymous_struct_info=self.param_anonymous_struct_infos.get(index),
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
        struct_qualified_name: str | None = None,
        anonymous_struct_info: AnonymousStructTypeInfo | None = None,
    ) -> str:
        return value_type_suffix(
            base_type,
            array_info=array_info,
            dict_info=dict_info,
            set_info=set_info,
            tuple_info=tuple_info,
            callable_info=callable_info,
            struct_qualified_name=struct_qualified_name,
            anonymous_struct_info=anonymous_struct_info,
        )


def value_type_key(
    base_type: BaseType,
    *,
    array_info: ArrayTypeInfo | None = None,
    dict_info: DictTypeInfo | None = None,
    set_info: SetTypeInfo | None = None,
    tuple_info: TupleTypeInfo | None = None,
    callable_info: CallableTypeInfo | None = None,
    struct_qualified_name: str | None = None,
    anonymous_struct_info: AnonymousStructTypeInfo | None = None,
) -> tuple:
    """Return a stable structural key for any Zinc value type."""
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
    if base_type == BaseType.STRUCT:
        if anonymous_struct_info:
            return ("anon_struct", anonymous_struct_info.structural_key())
        if struct_qualified_name:
            return ("named_struct", struct_qualified_name)
        return ("struct",)
    if base_type == BaseType.VOID:
        return ("unit",)
    if base_type == BaseType.NEVER:
        return ("never",)
    if base_type == BaseType.CONTEXT:
        return ("context",)
    return (base_type.name.lower(),)


def value_type_suffix(
    base_type: BaseType,
    *,
    array_info: ArrayTypeInfo | None = None,
    dict_info: DictTypeInfo | None = None,
    set_info: SetTypeInfo | None = None,
    tuple_info: TupleTypeInfo | None = None,
    callable_info: CallableTypeInfo | None = None,
    struct_qualified_name: str | None = None,
    anonymous_struct_info: AnonymousStructTypeInfo | None = None,
) -> str:
    """Return a Rust-safe suffix for any Zinc value type."""
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
    if base_type == BaseType.STRUCT:
        if anonymous_struct_info:
            return anonymous_struct_info.to_rust_type_suffix()
        return _named_struct_suffix(struct_qualified_name)
    if base_type == BaseType.VOID:
        return "Unit"
    if base_type == BaseType.NEVER:
        return "Never"
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
