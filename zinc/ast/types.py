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
    ENUM = auto()  # Enum type
    RESULT = auto()  # Builtin Result<T, E>
    OPTION = auto()  # Builtin Option<T>
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
    from zinc.numeric_literals import parse_numeric_literal

    if is_string_literal(literal_text):
        return BaseType.STRING
    if literal_text in ("true", "false"):
        return BaseType.BOOLEAN
    parsed = parse_numeric_literal(literal_text)
    if parsed is not None:
        return parsed.base_type
    raise ValueError(f"Unknown literal type: {literal_text}")


def type_to_rust(base_type: BaseType) -> str:
    """Convert a BaseType to its Rust type name."""
    mapping = {
        BaseType.INTEGER: "i64",
        BaseType.FLOAT: "f64",
        BaseType.STRING: "String",
        BaseType.BOOLEAN: "bool",
        BaseType.CHANNEL: "Channel",  # Generic, element type handled separately
        BaseType.CONTEXT: "Context",
        BaseType.ARRAY: "Vec",  # Generic, element type handled separately
        BaseType.DICT: "HashMap",  # Generic, key/value handled separately
        BaseType.SET: "HashSet",  # Generic, element type handled separately
        BaseType.TUPLE: "Tuple",  # Generic, element types handled separately
        BaseType.CALLABLE: "Callable",  # Placeholder, signature handled separately
        BaseType.STRUCT: "Struct",
        BaseType.ENUM: "Enum",
        BaseType.RESULT: "Result",
        BaseType.OPTION: "Option",
        BaseType.VOID: "()",
        BaseType.NEVER: "!",
        BaseType.UNKNOWN: "unknown",
    }
    return mapping.get(base_type, "unknown")


def normalize_exact_type(type_name: str | None) -> str | None:
    """Normalize a scalar exact type name to the Rust spelling used in codegen."""
    if type_name is None:
        return None
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
        "usize": "usize",
        "isize": "isize",
        "f8": "f8",
        "f16": "f16",
        "f32": "f32",
        "f64": "f64",
        "f128": "f128",
        "string": "String",
        "String": "String",
        "bool": "bool",
        "Context": "Context",
        "context": "Context",
    }
    return mapping.get(type_name, type_name)


def exact_type_to_base(type_name: str | None) -> BaseType:
    """Map an exact scalar type name to a Zinc base type."""
    normalized = normalize_exact_type(type_name)
    mapping = {
        "i8": BaseType.INTEGER,
        "i16": BaseType.INTEGER,
        "i32": BaseType.INTEGER,
        "i64": BaseType.INTEGER,
        "i128": BaseType.INTEGER,
        "u8": BaseType.INTEGER,
        "u16": BaseType.INTEGER,
        "u32": BaseType.INTEGER,
        "u64": BaseType.INTEGER,
        "u128": BaseType.INTEGER,
        "usize": BaseType.INTEGER,
        "isize": BaseType.INTEGER,
        "f8": BaseType.FLOAT,
        "f16": BaseType.FLOAT,
        "f32": BaseType.FLOAT,
        "f64": BaseType.FLOAT,
        "f128": BaseType.FLOAT,
        "String": BaseType.STRING,
        "bool": BaseType.BOOLEAN,
        "Context": BaseType.CONTEXT,
    }
    return mapping.get(normalized, BaseType.UNKNOWN)


def default_exact_type(base_type: BaseType) -> str | None:
    """Return the default exact scalar type used for unannotated primitive values."""
    mapping = {
        BaseType.INTEGER: "i64",
        BaseType.FLOAT: "f64",
        BaseType.STRING: "String",
        BaseType.BOOLEAN: "bool",
        BaseType.CONTEXT: "Context",
    }
    return mapping.get(base_type)


def exact_type_to_rust(exact_type: str | None, base_type: BaseType) -> str:
    """Render an exact scalar type, falling back to the base-type default."""
    if base_type == BaseType.ENUM:
        return _named_enum_rust_name(exact_type)
    normalized = normalize_exact_type(exact_type)
    if normalized is not None:
        return normalized
    return type_to_rust(base_type)


def _numeric_type_parts(type_name: str | None) -> tuple[str, int] | None:
    """Return the family/bits for a normalized numeric exact type."""
    normalized = normalize_exact_type(type_name)
    if normalized is None or len(normalized) < 2:
        return None
    family = normalized[0]
    if family not in {"i", "u", "f"}:
        return None
    try:
        return family, int(normalized[1:])
    except ValueError:
        return None


def promote_exact_numeric(left: str | None, right: str | None, result_base: BaseType) -> str | None:
    """Promote exact numeric spellings for expression results."""
    left = normalize_exact_type(left) or default_exact_type(result_base)
    right = normalize_exact_type(right) or default_exact_type(result_base)
    if left is None:
        return right
    if right is None:
        return left
    if left == right:
        return left
    left_parts = _numeric_type_parts(left)
    right_parts = _numeric_type_parts(right)
    if left_parts is None or right_parts is None:
        return default_exact_type(result_base)
    left_family, left_bits = left_parts
    right_family, right_bits = right_parts
    if result_base == BaseType.FLOAT:
        float_bits = max(
            left_bits if left_family == "f" else 32,
            right_bits if right_family == "f" else 32,
        )
        return f"f{float_bits}"
    if result_base == BaseType.INTEGER:
        if left_family == right_family:
            return f"{left_family}{max(left_bits, right_bits)}"
        return "i128"
    return default_exact_type(result_base)


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


def _named_enum_suffix(qualified_name: str | None) -> str:
    """Return a stable suffix fragment for a named enum identity."""
    if not qualified_name:
        return "Enum_unknown"
    return f"Enum_{_sanitize_type_fragment(qualified_name)}"


def _named_struct_rust_name(qualified_name: str | None) -> str:
    """Return a best-effort Rust type name for a named struct."""
    if not qualified_name:
        return "unknown"
    if "::extern::" in qualified_name:
        return qualified_name.rsplit("::", 1)[-1]
    module_id, sep, name = qualified_name.rpartition("::")
    if not sep:
        return qualified_name
    return f"{module_id.replace('/', '_')}__{name}"


def _named_enum_rust_name(qualified_name: str | None) -> str:
    """Return a best-effort Rust type name for a named enum."""
    if not qualified_name:
        return "unknown"
    module_id, sep, name = qualified_name.rpartition("::")
    if not sep:
        return qualified_name
    return f"{module_id.replace('/', '_')}__{name}"


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
    exact_type: str | None = None
    array_info: ArrayTypeInfo | None = None
    dict_info: DictTypeInfo | None = None
    set_info: SetTypeInfo | None = None
    tuple_info: TupleTypeInfo | None = None
    callable_info: CallableTypeInfo | None = None
    struct_qualified_name: str | None = None
    anonymous_struct_info: AnonymousStructTypeInfo | None = None
    result_info: ResultTypeInfo | None = None
    option_info: OptionTypeInfo | None = None

    def copy(self) -> AnonymousStructFieldInfo:
        """Deep-copy field metadata."""
        return AnonymousStructFieldInfo(
            name=self.name,
            resolved_type=self.resolved_type,
            exact_type=self.exact_type,
            array_info=self.array_info.copy() if self.array_info else None,
            dict_info=self.dict_info.copy() if self.dict_info else None,
            set_info=self.set_info.copy() if self.set_info else None,
            tuple_info=self.tuple_info.copy() if self.tuple_info else None,
            callable_info=self.callable_info.copy() if self.callable_info else None,
            struct_qualified_name=self.struct_qualified_name,
            anonymous_struct_info=self.anonymous_struct_info.copy() if self.anonymous_struct_info else None,
            result_info=self.result_info.copy() if self.result_info else None,
            option_info=self.option_info.copy() if self.option_info else None,
        )

    def structural_key(self) -> tuple[str, tuple]:
        """Return a stable structural key for this field."""
        return (
            self.name,
            value_type_key(
                self.resolved_type,
                exact_type=self.exact_type,
                array_info=self.array_info,
                dict_info=self.dict_info,
                set_info=self.set_info,
                tuple_info=self.tuple_info,
                callable_info=self.callable_info,
                struct_qualified_name=self.struct_qualified_name,
                anonymous_struct_info=self.anonymous_struct_info,
                result_info=self.result_info,
                option_info=self.option_info,
            ),
        )

    def rust_type_suffix(self) -> str:
        """Return a Rust-safe suffix fragment for this field type."""
        return value_type_suffix(
            self.resolved_type,
            exact_type=self.exact_type,
            array_info=self.array_info,
            dict_info=self.dict_info,
            set_info=self.set_info,
            tuple_info=self.tuple_info,
            callable_info=self.callable_info,
            struct_qualified_name=self.struct_qualified_name,
            anonymous_struct_info=self.anonymous_struct_info,
            result_info=self.result_info,
            option_info=self.option_info,
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
        parts = [f"{_sanitize_type_fragment(field.name)}_{field.rust_type_suffix()}" for field in self.canonical_fields()]
        return "AnonStruct_" + "_".join(parts)

    def rust_type_name(self) -> str:
        """Return the synthesized Rust type name for this shape."""
        return f"__ZincAnonStruct_{self.to_rust_type_suffix()}"


@dataclass
class ChannelTypeInfo:
    """Type information for channel types."""

    element_type: BaseType = BaseType.UNKNOWN  # Type of values sent/received
    element_exact_type: str | None = None
    element_tuple_info: TupleTypeInfo | None = None
    element_callable_info: CallableTypeInfo | None = None
    element_struct_qualified_name: str | None = None
    element_anonymous_struct_info: AnonymousStructTypeInfo | None = None
    element_result_info: ResultTypeInfo | None = None
    element_option_info: OptionTypeInfo | None = None
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
        if self.element_type == BaseType.RESULT and self.element_result_info:
            return self.element_result_info.to_rust_type()
        if self.element_type == BaseType.OPTION and self.element_option_info:
            return self.element_option_info.to_rust_type()
        return exact_type_to_rust(self.element_exact_type, self.element_type)

    def to_rust_type(self) -> str:
        """Generate the shared Rust channel-wrapper type."""
        return f"Channel<{self.element_rust_type()}>"

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
        if self.element_type == BaseType.RESULT and self.element_result_info:
            elem = self.element_result_info.to_rust_type_suffix()
            if self.is_bounded:
                return f"BoundedChannel_{elem}"
            return f"Channel_{elem}"
        if self.element_type == BaseType.OPTION and self.element_option_info:
            elem = self.element_option_info.to_rust_type_suffix()
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
            element_exact_type=self.element_exact_type,
            element_tuple_info=self.element_tuple_info.copy() if self.element_tuple_info else None,
            element_callable_info=self.element_callable_info.copy() if self.element_callable_info else None,
            element_struct_qualified_name=self.element_struct_qualified_name,
            element_anonymous_struct_info=self.element_anonymous_struct_info.copy() if self.element_anonymous_struct_info else None,
            element_result_info=self.element_result_info.copy() if self.element_result_info else None,
            element_option_info=self.element_option_info.copy() if self.element_option_info else None,
            is_bounded=self.is_bounded,
        )


@dataclass
class ArrayTypeInfo:
    """Type information for arrays."""

    element_type: BaseType = BaseType.UNKNOWN
    element_exact_type: str | None = None
    element_tuple_info: TupleTypeInfo | None = None
    element_callable_info: CallableTypeInfo | None = None
    element_struct_qualified_name: str | None = None
    element_anonymous_struct_info: AnonymousStructTypeInfo | None = None
    element_result_info: ResultTypeInfo | None = None
    element_option_info: OptionTypeInfo | None = None
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
        if self.element_type == BaseType.RESULT and self.element_result_info:
            return self.element_result_info.to_rust_type()
        if self.element_type == BaseType.OPTION and self.element_option_info:
            return self.element_option_info.to_rust_type()
        return exact_type_to_rust(self.element_exact_type, self.element_type)

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
        elif self.element_type == BaseType.RESULT and self.element_result_info:
            elem = self.element_result_info.to_rust_type_suffix()
        elif self.element_type == BaseType.OPTION and self.element_option_info:
            elem = self.element_option_info.to_rust_type_suffix()
        else:
            elem = exact_type_to_rust(self.element_exact_type, self.element_type)
        return f"Vec_{elem}"

    def copy(self) -> ArrayTypeInfo:
        """Deep-copy array metadata."""
        return ArrayTypeInfo(
            element_type=self.element_type,
            element_exact_type=self.element_exact_type,
            element_tuple_info=self.element_tuple_info.copy() if self.element_tuple_info else None,
            element_callable_info=self.element_callable_info.copy() if self.element_callable_info else None,
            element_struct_qualified_name=self.element_struct_qualified_name,
            element_anonymous_struct_info=self.element_anonymous_struct_info.copy() if self.element_anonymous_struct_info else None,
            element_result_info=self.element_result_info.copy() if self.element_result_info else None,
            element_option_info=self.element_option_info.copy() if self.element_option_info else None,
            is_mutated=self.is_mutated,
        )


@dataclass
class DictTypeInfo:
    """Type information for dict/sort_dict containers."""

    key_type: BaseType = BaseType.UNKNOWN
    value_type: BaseType = BaseType.UNKNOWN
    key_exact_type: str | None = None
    value_exact_type: str | None = None
    key_callable_info: CallableTypeInfo | None = None
    value_callable_info: CallableTypeInfo | None = None
    key_struct_qualified_name: str | None = None
    value_struct_qualified_name: str | None = None
    key_anonymous_struct_info: AnonymousStructTypeInfo | None = None
    value_anonymous_struct_info: AnonymousStructTypeInfo | None = None
    key_result_info: ResultTypeInfo | None = None
    value_result_info: ResultTypeInfo | None = None
    key_option_info: OptionTypeInfo | None = None
    value_option_info: OptionTypeInfo | None = None
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
        elif self.key_type == BaseType.RESULT and self.key_result_info:
            key = self.key_result_info.to_rust_type()
        elif self.key_type == BaseType.OPTION and self.key_option_info:
            key = self.key_option_info.to_rust_type()
        else:
            key = exact_type_to_rust(self.key_exact_type, self.key_type)
        if self.value_type == BaseType.CALLABLE and self.value_callable_info:
            value = self.value_callable_info.rust_type_name()
        elif self.value_type == BaseType.STRUCT:
            if self.value_anonymous_struct_info:
                value = self.value_anonymous_struct_info.rust_type_name()
            else:
                value = _named_struct_rust_name(self.value_struct_qualified_name)
        elif self.value_type == BaseType.RESULT and self.value_result_info:
            value = self.value_result_info.to_rust_type()
        elif self.value_type == BaseType.OPTION and self.value_option_info:
            value = self.value_option_info.to_rust_type()
        else:
            value = exact_type_to_rust(self.value_exact_type, self.value_type)
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
        elif self.key_type == BaseType.RESULT and self.key_result_info:
            key = self.key_result_info.to_rust_type_suffix()
        elif self.key_type == BaseType.OPTION and self.key_option_info:
            key = self.key_option_info.to_rust_type_suffix()
        else:
            key = exact_type_to_rust(self.key_exact_type, self.key_type)
        if self.value_type == BaseType.CALLABLE and self.value_callable_info:
            value = self.value_callable_info.to_rust_type_suffix()
        elif self.value_type == BaseType.STRUCT:
            value = value_type_suffix(
                BaseType.STRUCT,
                struct_qualified_name=self.value_struct_qualified_name,
                anonymous_struct_info=self.value_anonymous_struct_info,
            )
        elif self.value_type == BaseType.RESULT and self.value_result_info:
            value = self.value_result_info.to_rust_type_suffix()
        elif self.value_type == BaseType.OPTION and self.value_option_info:
            value = self.value_option_info.to_rust_type_suffix()
        else:
            value = exact_type_to_rust(self.value_exact_type, self.value_type)
        return f"{self.rust_container()}_{key}_{value}"

    def copy(self) -> DictTypeInfo:
        """Deep-copy dict metadata."""
        return DictTypeInfo(
            key_type=self.key_type,
            value_type=self.value_type,
            key_exact_type=self.key_exact_type,
            value_exact_type=self.value_exact_type,
            key_callable_info=self.key_callable_info.copy() if self.key_callable_info else None,
            value_callable_info=self.value_callable_info.copy() if self.value_callable_info else None,
            key_struct_qualified_name=self.key_struct_qualified_name,
            value_struct_qualified_name=self.value_struct_qualified_name,
            key_anonymous_struct_info=self.key_anonymous_struct_info.copy() if self.key_anonymous_struct_info else None,
            value_anonymous_struct_info=self.value_anonymous_struct_info.copy() if self.value_anonymous_struct_info else None,
            key_result_info=self.key_result_info.copy() if self.key_result_info else None,
            value_result_info=self.value_result_info.copy() if self.value_result_info else None,
            key_option_info=self.key_option_info.copy() if self.key_option_info else None,
            value_option_info=self.value_option_info.copy() if self.value_option_info else None,
            kind=self.kind,
            is_mutated=self.is_mutated,
        )


@dataclass
class SetTypeInfo:
    """Type information for set/sort_set containers."""

    element_type: BaseType = BaseType.UNKNOWN
    element_exact_type: str | None = None
    element_struct_qualified_name: str | None = None
    element_anonymous_struct_info: AnonymousStructTypeInfo | None = None
    element_result_info: ResultTypeInfo | None = None
    element_option_info: OptionTypeInfo | None = None
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
        elif self.element_type == BaseType.RESULT and self.element_result_info:
            elem = self.element_result_info.to_rust_type()
        elif self.element_type == BaseType.OPTION and self.element_option_info:
            elem = self.element_option_info.to_rust_type()
        else:
            elem = exact_type_to_rust(self.element_exact_type, self.element_type)
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
        elif self.element_type == BaseType.RESULT and self.element_result_info:
            elem = self.element_result_info.to_rust_type_suffix()
        elif self.element_type == BaseType.OPTION and self.element_option_info:
            elem = self.element_option_info.to_rust_type_suffix()
        else:
            elem = exact_type_to_rust(self.element_exact_type, self.element_type)
        return f"{self.rust_container()}_{elem}"

    def copy(self) -> SetTypeInfo:
        """Deep-copy set metadata."""
        return SetTypeInfo(
            element_type=self.element_type,
            element_exact_type=self.element_exact_type,
            element_struct_qualified_name=self.element_struct_qualified_name,
            element_anonymous_struct_info=self.element_anonymous_struct_info.copy() if self.element_anonymous_struct_info else None,
            element_result_info=self.element_result_info.copy() if self.element_result_info else None,
            element_option_info=self.element_option_info.copy() if self.element_option_info else None,
            kind=self.kind,
            is_mutated=self.is_mutated,
        )


@dataclass
class TupleTypeInfo:
    """Type information for tuple values."""

    element_types: list[BaseType] = field(default_factory=list)
    element_exact_types: list[str | None] = field(default_factory=list)
    element_tuple_infos: dict[int, TupleTypeInfo] = field(default_factory=dict)
    element_callable_infos: dict[int, CallableTypeInfo] = field(default_factory=dict)
    element_struct_qualified_names: dict[int, str] = field(default_factory=dict)
    element_anonymous_struct_infos: dict[int, AnonymousStructTypeInfo] = field(default_factory=dict)
    element_result_infos: dict[int, ResultTypeInfo] = field(default_factory=dict)
    element_option_infos: dict[int, OptionTypeInfo] = field(default_factory=dict)

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
        if element_type == BaseType.RESULT and index in self.element_result_infos:
            return self.element_result_infos[index].to_rust_type()
        if element_type == BaseType.OPTION and index in self.element_option_infos:
            return self.element_option_infos[index].to_rust_type()
        exact_type = self.element_exact_types[index] if index < len(self.element_exact_types) else None
        return exact_type_to_rust(exact_type, element_type)

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
        if element_type == BaseType.RESULT and index in self.element_result_infos:
            return self.element_result_infos[index].to_rust_type_suffix()
        if element_type == BaseType.OPTION and index in self.element_option_infos:
            return self.element_option_infos[index].to_rust_type_suffix()
        exact_type = self.element_exact_types[index] if index < len(self.element_exact_types) else None
        return exact_type_to_rust(exact_type, element_type)

    def to_rust_type_suffix(self) -> str:
        """Generate type suffix for mangled names."""
        if not self.element_types:
            return "Tuple_empty"
        return "Tuple_" + "_".join(self.element_type_suffix(i) for i in range(len(self.element_types)))

    def copy(self) -> TupleTypeInfo:
        """Deep-copy tuple metadata."""
        return TupleTypeInfo(
            element_types=list(self.element_types),
            element_exact_types=list(self.element_exact_types),
            element_tuple_infos={index: info.copy() for index, info in self.element_tuple_infos.items()},
            element_callable_infos={index: info.copy() for index, info in self.element_callable_infos.items()},
            element_struct_qualified_names=dict(self.element_struct_qualified_names),
            element_anonymous_struct_infos={index: info.copy() for index, info in self.element_anonymous_struct_infos.items()},
            element_result_infos={index: info.copy() for index, info in self.element_result_infos.items()},
            element_option_infos={index: info.copy() for index, info in self.element_option_infos.items()},
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
    param_exact_types: list[str | None] = field(default_factory=list)
    param_names: list[str] = field(default_factory=list)
    param_default_texts: dict[int, str] = field(default_factory=dict)
    param_default_exprs: dict[int, object] = field(default_factory=dict)
    param_default_owner_modules: dict[int, str] = field(default_factory=dict)
    param_array_infos: dict[int, ArrayTypeInfo] = field(default_factory=dict)
    param_dict_infos: dict[int, DictTypeInfo] = field(default_factory=dict)
    param_set_infos: dict[int, SetTypeInfo] = field(default_factory=dict)
    param_tuple_infos: dict[int, TupleTypeInfo] = field(default_factory=dict)
    param_callable_infos: dict[int, CallableTypeInfo] = field(default_factory=dict)
    param_struct_qualified_names: dict[int, str] = field(default_factory=dict)
    param_anonymous_struct_infos: dict[int, AnonymousStructTypeInfo] = field(default_factory=dict)
    param_result_infos: dict[int, ResultTypeInfo] = field(default_factory=dict)
    param_option_infos: dict[int, OptionTypeInfo] = field(default_factory=dict)
    return_type: BaseType = BaseType.UNKNOWN
    return_exact_type: str | None = None
    return_dict_info: DictTypeInfo | None = None
    return_set_info: SetTypeInfo | None = None
    return_tuple_info: TupleTypeInfo | None = None
    return_callable_info: CallableTypeInfo | None = None
    return_struct_qualified_name: str | None = None
    return_anonymous_struct_info: AnonymousStructTypeInfo | None = None
    return_result_info: ResultTypeInfo | None = None
    return_option_info: OptionTypeInfo | None = None
    targets: tuple[CallableTarget, ...] = ()

    def copy(self) -> CallableTypeInfo:
        """Deep-copy callable metadata."""
        return CallableTypeInfo(
            param_types=list(self.param_types),
            param_exact_types=list(self.param_exact_types),
            param_names=list(self.param_names),
            param_default_texts=dict(self.param_default_texts),
            param_default_exprs=dict(self.param_default_exprs),
            param_default_owner_modules=dict(self.param_default_owner_modules),
            param_array_infos={index: info.copy() for index, info in self.param_array_infos.items()},
            param_dict_infos={index: info.copy() for index, info in self.param_dict_infos.items()},
            param_set_infos={index: info.copy() for index, info in self.param_set_infos.items()},
            param_tuple_infos={index: info.copy() for index, info in self.param_tuple_infos.items()},
            param_callable_infos={index: info.copy() for index, info in self.param_callable_infos.items() if info is not None},
            param_struct_qualified_names=dict(self.param_struct_qualified_names),
            param_anonymous_struct_infos={index: info.copy() for index, info in self.param_anonymous_struct_infos.items()},
            param_result_infos={index: info.copy() for index, info in self.param_result_infos.items()},
            param_option_infos={index: info.copy() for index, info in self.param_option_infos.items()},
            return_type=self.return_type,
            return_exact_type=self.return_exact_type,
            return_dict_info=self.return_dict_info.copy() if self.return_dict_info else None,
            return_set_info=self.return_set_info.copy() if self.return_set_info else None,
            return_tuple_info=self.return_tuple_info.copy() if self.return_tuple_info else None,
            return_callable_info=self.return_callable_info.copy() if self.return_callable_info else None,
            return_struct_qualified_name=self.return_struct_qualified_name,
            return_anonymous_struct_info=self.return_anonymous_struct_info.copy() if self.return_anonymous_struct_info else None,
            return_result_info=self.return_result_info.copy() if self.return_result_info else None,
            return_option_info=self.return_option_info.copy() if self.return_option_info else None,
            targets=tuple(self.targets),
        )

    def structural_key(self) -> tuple:
        """Return a stable signature key that ignores concrete target identity."""
        return (
            tuple(self._param_key(index, base_type) for index, base_type in enumerate(self.param_types)),
            self._value_key(
                self.return_type,
                exact_type=self.return_exact_type,
                dict_info=self.return_dict_info,
                set_info=self.return_set_info,
                tuple_info=self.return_tuple_info,
                callable_info=self.return_callable_info,
                struct_qualified_name=self.return_struct_qualified_name,
                anonymous_struct_info=self.return_anonymous_struct_info,
                result_info=self.return_result_info,
                option_info=self.return_option_info,
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
        merged._merge_call_metadata_from(other)
        seen = {target.storage_key() for target in merged.targets}
        for target in other.targets:
            if target.storage_key() not in seen:
                merged.targets = (*merged.targets, target)
                seen.add(target.storage_key())
        return merged

    def _merge_call_metadata_from(self, other: CallableTypeInfo) -> None:
        """Merge parameter names/defaults without changing callable type identity."""
        if self.param_names and other.param_names and self.param_names != other.param_names:
            self.param_names = []
            self.param_default_texts = {}
            self.param_default_exprs = {}
            self.param_default_owner_modules = {}
            return
        if not self.param_names and other.param_names:
            self.param_names = list(other.param_names)

        if bool(self.param_default_texts) != bool(other.param_default_texts):
            self.param_default_texts = {}
            self.param_default_exprs = {}
            self.param_default_owner_modules = {}
            return
        if self.param_default_texts and other.param_default_texts and self.param_default_texts != other.param_default_texts:
            self.param_default_texts = {}
            self.param_default_exprs = {}
            self.param_default_owner_modules = {}
            return

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
            struct_qualified_name=self.return_struct_qualified_name,
            anonymous_struct_info=self.return_anonymous_struct_info,
            result_info=self.return_result_info,
            option_info=self.return_option_info,
        )
        return f"{params_part}_to_{return_part}"

    def _param_key(self, index: int, base_type: BaseType) -> tuple:
        return self._value_key(
            base_type,
            exact_type=self.param_exact_types[index] if index < len(self.param_exact_types) else None,
            array_info=self.param_array_infos.get(index),
            dict_info=self.param_dict_infos.get(index),
            set_info=self.param_set_infos.get(index),
            tuple_info=self.param_tuple_infos.get(index),
            callable_info=self.param_callable_infos.get(index),
            struct_qualified_name=self.param_struct_qualified_names.get(index),
            anonymous_struct_info=self.param_anonymous_struct_infos.get(index),
            result_info=self.param_result_infos.get(index),
            option_info=self.param_option_infos.get(index),
        )

    def _value_key(
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
    ) -> tuple:
        return value_type_key(
            base_type,
            exact_type=exact_type,
            array_info=array_info,
            dict_info=dict_info,
            set_info=set_info,
            tuple_info=tuple_info,
            callable_info=callable_info,
            struct_qualified_name=struct_qualified_name,
            anonymous_struct_info=anonymous_struct_info,
            result_info=result_info,
            option_info=option_info,
        )

    def _param_suffix(self, index: int, base_type: BaseType) -> str:
        return self._value_suffix(
            base_type,
            exact_type=self.param_exact_types[index] if index < len(self.param_exact_types) else None,
            array_info=self.param_array_infos.get(index),
            dict_info=self.param_dict_infos.get(index),
            set_info=self.param_set_infos.get(index),
            tuple_info=self.param_tuple_infos.get(index),
            callable_info=self.param_callable_infos.get(index),
            struct_qualified_name=self.param_struct_qualified_names.get(index),
            anonymous_struct_info=self.param_anonymous_struct_infos.get(index),
            result_info=self.param_result_infos.get(index),
            option_info=self.param_option_infos.get(index),
        )

    def _value_suffix(
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
    ) -> str:
        return value_type_suffix(
            base_type,
            exact_type=exact_type,
            array_info=array_info,
            dict_info=dict_info,
            set_info=set_info,
            tuple_info=tuple_info,
            callable_info=callable_info,
            struct_qualified_name=struct_qualified_name,
            anonymous_struct_info=anonymous_struct_info,
            result_info=result_info,
            option_info=option_info,
        )


@dataclass
class ValueTypeSpec:
    """A reusable rich description for any Zinc value type."""

    base_type: BaseType = BaseType.UNKNOWN
    exact_type: str | None = None
    array_info: ArrayTypeInfo | None = None
    channel_info: ChannelTypeInfo | None = None
    dict_info: DictTypeInfo | None = None
    set_info: SetTypeInfo | None = None
    tuple_info: TupleTypeInfo | None = None
    callable_info: CallableTypeInfo | None = None
    struct_qualified_name: str | None = None
    anonymous_struct_info: AnonymousStructTypeInfo | None = None
    result_info: ResultTypeInfo | None = None
    option_info: OptionTypeInfo | None = None

    def copy(self) -> ValueTypeSpec:
        """Deep-copy nested value metadata."""
        return ValueTypeSpec(
            base_type=self.base_type,
            exact_type=self.exact_type,
            array_info=self.array_info.copy() if self.array_info else None,
            channel_info=self.channel_info.copy() if self.channel_info else None,
            dict_info=self.dict_info.copy() if self.dict_info else None,
            set_info=self.set_info.copy() if self.set_info else None,
            tuple_info=self.tuple_info.copy() if self.tuple_info else None,
            callable_info=self.callable_info.copy() if self.callable_info else None,
            struct_qualified_name=self.struct_qualified_name,
            anonymous_struct_info=self.anonymous_struct_info.copy() if self.anonymous_struct_info else None,
            result_info=self.result_info.copy() if self.result_info else None,
            option_info=self.option_info.copy() if self.option_info else None,
        )

    def to_rust_type(self) -> str:
        """Render this value as a Rust type."""
        if self.base_type == BaseType.ARRAY and self.array_info:
            return self.array_info.to_rust_type(as_reference=False)
        if self.base_type == BaseType.CHANNEL and self.channel_info:
            return self.channel_info.to_rust_type()
        if self.base_type == BaseType.DICT and self.dict_info:
            return self.dict_info.to_rust_type(as_reference=False)
        if self.base_type == BaseType.SET and self.set_info:
            return self.set_info.to_rust_type(as_reference=False)
        if self.base_type == BaseType.TUPLE and self.tuple_info:
            return self.tuple_info.to_rust_type()
        if self.base_type == BaseType.CALLABLE and self.callable_info:
            return self.callable_info.rust_type_name()
        if self.base_type == BaseType.STRUCT:
            if self.anonymous_struct_info:
                return self.anonymous_struct_info.rust_type_name()
            return _named_struct_rust_name(self.struct_qualified_name)
        if self.base_type == BaseType.ENUM:
            return _named_enum_rust_name(self.exact_type)
        if self.base_type == BaseType.RESULT and self.result_info:
            return self.result_info.to_rust_type()
        if self.base_type == BaseType.OPTION and self.option_info:
            return self.option_info.to_rust_type()
        return exact_type_to_rust(self.exact_type, self.base_type)

    def structural_key(self) -> tuple:
        """Return a stable structural key for this value."""
        return value_type_key(
            self.base_type,
            exact_type=self.exact_type,
            array_info=self.array_info,
            channel_info=self.channel_info,
            dict_info=self.dict_info,
            set_info=self.set_info,
            tuple_info=self.tuple_info,
            callable_info=self.callable_info,
            struct_qualified_name=self.struct_qualified_name,
            anonymous_struct_info=self.anonymous_struct_info,
            result_info=self.result_info,
            option_info=self.option_info,
        )

    def to_rust_type_suffix(self) -> str:
        """Return a stable Rust-safe suffix for this value."""
        return value_type_suffix(
            self.base_type,
            exact_type=self.exact_type,
            array_info=self.array_info,
            channel_info=self.channel_info,
            dict_info=self.dict_info,
            set_info=self.set_info,
            tuple_info=self.tuple_info,
            callable_info=self.callable_info,
            struct_qualified_name=self.struct_qualified_name,
            anonymous_struct_info=self.anonymous_struct_info,
            result_info=self.result_info,
            option_info=self.option_info,
        )


@dataclass
class ResultTypeInfo:
    """Type information for builtin Result<T, E> values."""

    ok_type: ValueTypeSpec = field(default_factory=ValueTypeSpec)
    err_type: ValueTypeSpec = field(default_factory=ValueTypeSpec)

    def copy(self) -> ResultTypeInfo:
        """Deep-copy result metadata."""
        return ResultTypeInfo(
            ok_type=self.ok_type.copy(),
            err_type=self.err_type.copy(),
        )

    def to_rust_type(self) -> str:
        """Render this result as a Rust type."""
        return f"Result<{self.ok_type.to_rust_type()}, {self.err_type.to_rust_type()}>"

    def to_rust_type_suffix(self) -> str:
        """Return a stable Rust-safe suffix for this result."""
        return f"Result_{self.ok_type.to_rust_type_suffix()}_{self.err_type.to_rust_type_suffix()}"

    def structural_key(self) -> tuple:
        """Return a stable structural key for this result."""
        return ("result", self.ok_type.structural_key(), self.err_type.structural_key())


@dataclass
class OptionTypeInfo:
    """Type information for builtin Option<T> values."""

    some_type: ValueTypeSpec = field(default_factory=ValueTypeSpec)

    def copy(self) -> OptionTypeInfo:
        """Deep-copy option metadata."""
        return OptionTypeInfo(some_type=self.some_type.copy())

    def to_rust_type(self) -> str:
        """Render this option as a Rust type."""
        return f"Option<{self.some_type.to_rust_type()}>"

    def to_rust_type_suffix(self) -> str:
        """Return a stable Rust-safe suffix for this option."""
        return f"Option_{self.some_type.to_rust_type_suffix()}"

    def structural_key(self) -> tuple:
        """Return a stable structural key for this option."""
        return ("option", self.some_type.structural_key())


def value_type_key(
    base_type: BaseType,
    *,
    exact_type: str | None = None,
    array_info: ArrayTypeInfo | None = None,
    channel_info: ChannelTypeInfo | None = None,
    dict_info: DictTypeInfo | None = None,
    set_info: SetTypeInfo | None = None,
    tuple_info: TupleTypeInfo | None = None,
    callable_info: CallableTypeInfo | None = None,
    struct_qualified_name: str | None = None,
    anonymous_struct_info: AnonymousStructTypeInfo | None = None,
    result_info: ResultTypeInfo | None = None,
    option_info: OptionTypeInfo | None = None,
) -> tuple:
    """Return a stable structural key for any Zinc value type."""
    if base_type == BaseType.ARRAY and array_info:
        return ("array", array_info.to_rust_type_suffix())
    if base_type == BaseType.CHANNEL and channel_info:
        return ("channel", channel_info.to_rust_type_suffix())
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
    if base_type == BaseType.ENUM:
        normalized_exact = normalize_exact_type(exact_type)
        if normalized_exact is not None:
            return ("enum", normalized_exact)
        return ("enum",)
    if base_type == BaseType.RESULT and result_info:
        return result_info.structural_key()
    if base_type == BaseType.OPTION and option_info:
        return option_info.structural_key()
    if base_type == BaseType.VOID:
        return ("unit",)
    if base_type == BaseType.NEVER:
        return ("never",)
    if base_type == BaseType.CONTEXT:
        return ("context",)
    normalized_exact = normalize_exact_type(exact_type)
    if normalized_exact is not None:
        return (base_type.name.lower(), normalized_exact)
    return (base_type.name.lower(),)


def value_type_suffix(
    base_type: BaseType,
    *,
    exact_type: str | None = None,
    array_info: ArrayTypeInfo | None = None,
    channel_info: ChannelTypeInfo | None = None,
    dict_info: DictTypeInfo | None = None,
    set_info: SetTypeInfo | None = None,
    tuple_info: TupleTypeInfo | None = None,
    callable_info: CallableTypeInfo | None = None,
    struct_qualified_name: str | None = None,
    anonymous_struct_info: AnonymousStructTypeInfo | None = None,
    result_info: ResultTypeInfo | None = None,
    option_info: OptionTypeInfo | None = None,
) -> str:
    """Return a Rust-safe suffix for any Zinc value type."""
    if base_type == BaseType.ARRAY and array_info:
        return array_info.to_rust_type_suffix()
    if base_type == BaseType.CHANNEL and channel_info:
        return channel_info.to_rust_type_suffix()
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
    if base_type == BaseType.ENUM:
        return _named_enum_suffix(exact_type)
    if base_type == BaseType.RESULT and result_info:
        return result_info.to_rust_type_suffix()
    if base_type == BaseType.OPTION and option_info:
        return option_info.to_rust_type_suffix()
    if base_type == BaseType.VOID:
        return "Unit"
    if base_type == BaseType.NEVER:
        return "Never"
    if base_type == BaseType.CONTEXT:
        return "Context"
    return exact_type_to_rust(exact_type, base_type)


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
