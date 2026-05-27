"""Compile-time metadata value model and generated Rust runtime helpers."""

from __future__ import annotations

from dataclasses import dataclass, field

from zinc.ast.types import AnonymousStructTypeInfo, BaseType

META_NAMESPACE = "__zinc_meta"

TYPE_META_QNAME = f"{META_NAMESPACE}::TypeMeta"
CHANNEL_META_QNAME = f"{META_NAMESPACE}::ChannelMeta"
STRUCT_META_QNAME = f"{META_NAMESPACE}::StructMeta"
ENUM_META_QNAME = f"{META_NAMESPACE}::EnumMeta"
VARIANT_META_QNAME = f"{META_NAMESPACE}::VariantMeta"
FIELD_META_QNAME = f"{META_NAMESPACE}::FieldMeta"
FUNCTION_META_QNAME = f"{META_NAMESPACE}::FunctionMeta"
BUILTIN_META_QNAME = f"{META_NAMESPACE}::BuiltinMeta"
METHOD_META_QNAME = f"{META_NAMESPACE}::MethodMeta"
FUNCTION_PARAM_META_QNAME = f"{META_NAMESPACE}::FunctionParameterMeta"
METHOD_PARAM_META_QNAME = f"{META_NAMESPACE}::MethodParameterMeta"
VARIABLE_META_QNAME = f"{META_NAMESPACE}::VariableMeta"
CONST_META_QNAME = f"{META_NAMESPACE}::ConstMeta"
COMPONENT_ORDER_QNAME = f"{META_NAMESPACE}::ComponentOrder"

META_STRUCT_QNAMES = {
    TYPE_META_QNAME,
    CHANNEL_META_QNAME,
    STRUCT_META_QNAME,
    ENUM_META_QNAME,
    VARIANT_META_QNAME,
    FIELD_META_QNAME,
    FUNCTION_META_QNAME,
    BUILTIN_META_QNAME,
    METHOD_META_QNAME,
    FUNCTION_PARAM_META_QNAME,
    METHOD_PARAM_META_QNAME,
    VARIABLE_META_QNAME,
    CONST_META_QNAME,
}

COMPONENT_ORDER_VARIANTS = {
    "depth_first": "DepthFirst",
    "breadth_first": "BreadthFirst",
    "topological": "Topological",
}


def is_meta_struct_qname(qualified_name: str | None) -> bool:
    """Return True when a struct identity belongs to the metadata runtime."""
    return qualified_name in META_STRUCT_QNAMES


def is_type_meta_qname(qualified_name: str | None) -> bool:
    """Return True when a metadata object is a TypeMeta-family value."""
    return qualified_name in {TYPE_META_QNAME, CHANNEL_META_QNAME}


def meta_struct_rust_name(qualified_name: str | None) -> str:
    """Return the generated Rust type name for a metadata struct."""
    mapping = {
        TYPE_META_QNAME: "__ZincTypeMeta",
        CHANNEL_META_QNAME: "__ZincTypeMeta",
        STRUCT_META_QNAME: "__ZincStructMeta",
        ENUM_META_QNAME: "__ZincEnumMeta",
        VARIANT_META_QNAME: "__ZincVariantMeta",
        FIELD_META_QNAME: "__ZincFieldMeta",
        FUNCTION_META_QNAME: "__ZincFunctionMeta",
        BUILTIN_META_QNAME: "__ZincBuiltinMeta",
        METHOD_META_QNAME: "__ZincMethodMeta",
        FUNCTION_PARAM_META_QNAME: "__ZincFunctionParameterMeta",
        METHOD_PARAM_META_QNAME: "__ZincMethodParameterMeta",
        VARIABLE_META_QNAME: "__ZincVariableMeta",
        CONST_META_QNAME: "__ZincConstMeta",
        COMPONENT_ORDER_QNAME: "__ZincComponentOrder",
    }
    return mapping.get(qualified_name, "__ZincMetaUnknown")


@dataclass
class MetaListValue:
    """Typed compile-time list used by metadata fields and methods."""

    items: list[object] = field(default_factory=list)
    element_base_type: BaseType = BaseType.UNKNOWN
    element_exact_type: str | None = None
    element_struct_qualified_name: str | None = None
    element_anonymous_struct_info: AnonymousStructTypeInfo | None = None


@dataclass(eq=False)
class MetaValue:
    """One compile-time metadata object returned by Zinc builtins."""

    struct_qualified_name: str
    fields: dict[str, object] = field(default_factory=dict)
    methods: dict[str, object] = field(default_factory=dict)

    def get_field(self, name: str) -> object:
        """Return one public field value."""
        return self.fields[name]

    def has_field(self, name: str) -> bool:
        """Return True when this metadata object exposes a public field."""
        return name in self.fields

    def call_method(self, name: str, args: list[object]) -> object:
        """Evaluate a compile-time metadata method."""
        target = self.methods[name]
        if callable(target):
            return target(args)
        if args:
            raise ValueError(f"metadata method '{name}' does not accept arguments")
        return target

    def has_method(self, name: str) -> bool:
        """Return True when this metadata object exposes a compile-time method."""
        return name in self.methods

    def __eq__(self, other: object) -> bool:
        """Compare metadata values by visible identity and fields, not helper closures."""
        if not isinstance(other, MetaValue):
            return NotImplemented
        return self.struct_qualified_name == other.struct_qualified_name and self.fields == other.fields


def unknown_type_meta(name: str = "unknown") -> MetaValue:
    """Return a generic unknown TypeMeta placeholder."""
    return MetaValue(
        struct_qualified_name=TYPE_META_QNAME,
        fields={
            "kind": "unknown",
            "name": name,
            "fqn": name,
            "family_name": name,
            "family_fqn": name,
            "args": MetaListValue(
                items=[],
                element_base_type=BaseType.STRUCT,
                element_struct_qualified_name=TYPE_META_QNAME,
            ),
            "is_named": False,
            "is_bounded": False,
            "infer_slots": MetaListValue(
                items=[],
                element_base_type=BaseType.STRING,
                element_exact_type="String",
            ),
        },
    )


def component_order_value(name: str) -> MetaValue:
    """Return the metadata enum value used by recursive_components()."""
    if name not in COMPONENT_ORDER_VARIANTS:
        raise ValueError(f"unknown component order '{name}'")
    return MetaValue(
        struct_qualified_name=COMPONENT_ORDER_QNAME,
        fields={
            "name": name,
        },
    )


def metadata_runtime_definitions() -> list[str]:
    """Return Rust helper definitions for Zinc metadata values."""
    return [
        "\n".join(
            [
                "#[derive(Clone, Debug, Default, PartialEq)]",
                "struct __ZincTypeMeta {",
                "    pub kind: String,",
                "    pub name: String,",
                "    pub fqn: String,",
                "    pub family_name: String,",
                "    pub family_fqn: String,",
                "    pub args: Vec<__ZincTypeMeta>,",
                "    pub is_named: bool,",
                "    pub is_bounded: bool,",
                "    pub infer_slots: Vec<String>,",
                "}",
            ]
        ),
        "\n".join(
            [
                "#[derive(Clone, Debug, Default, PartialEq)]",
                "struct __ZincStructMeta {",
                "    pub kind: String,",
                "    pub name: String,",
                "    pub fqn: String,",
                "    pub module_fqn: String,",
                "    pub file: String,",
                "    pub line_num: u32,",
                "    pub is_public: bool,",
                "    pub type_info: __ZincTypeMeta,",
                "}",
            ]
        ),
        "\n".join(
            [
                "#[derive(Clone, Debug, Default, PartialEq)]",
                "struct __ZincEnumMeta {",
                "    pub kind: String,",
                "    pub name: String,",
                "    pub fqn: String,",
                "    pub module_fqn: String,",
                "    pub file: String,",
                "    pub line_num: u32,",
                "    pub is_public: bool,",
                "    pub type_info: __ZincTypeMeta,",
                "}",
            ]
        ),
        "\n".join(
            [
                "#[derive(Clone, Debug, Default, PartialEq)]",
                "struct __ZincVariantMeta {",
                "    pub kind: String,",
                "    pub name: String,",
                "    pub fqn: String,",
                "    pub module_fqn: String,",
                "    pub file: String,",
                "    pub line_num: u32,",
                "    pub is_public: bool,",
                "    pub index: u32,",
                "}",
            ]
        ),
        "\n".join(
            [
                "#[derive(Clone, Debug, Default, PartialEq)]",
                "struct __ZincFieldMeta {",
                "    pub kind: String,",
                "    pub name: String,",
                "    pub fqn: String,",
                "    pub module_fqn: String,",
                "    pub file: String,",
                "    pub line_num: u32,",
                "    pub is_public: bool,",
                "    pub value_type: __ZincTypeMeta,",
                "    pub index: u32,",
                "    pub is_const: bool,",
                "    pub has_default: bool,",
                "    pub is_declared: bool,",
                "    pub source_component_fqn: String,",
                "}",
            ]
        ),
        "\n".join(
            [
                "#[derive(Clone, Debug, Default, PartialEq)]",
                "struct __ZincFunctionParameterMeta {",
                "    pub kind: String,",
                "    pub name: String,",
                "    pub fqn: String,",
                "    pub module_fqn: String,",
                "    pub file: String,",
                "    pub line_num: u32,",
                "    pub is_public: bool,",
                "    pub index: u32,",
                "    pub value_type: __ZincTypeMeta,",
                "    pub declared_type: __ZincTypeMeta,",
                "    pub has_declared_type: bool,",
                "}",
            ]
        ),
        "\n".join(
            [
                "#[derive(Clone, Debug, Default, PartialEq)]",
                "struct __ZincMethodParameterMeta {",
                "    pub kind: String,",
                "    pub name: String,",
                "    pub fqn: String,",
                "    pub module_fqn: String,",
                "    pub file: String,",
                "    pub line_num: u32,",
                "    pub is_public: bool,",
                "    pub index: u32,",
                "    pub value_type: __ZincTypeMeta,",
                "    pub declared_type: __ZincTypeMeta,",
                "    pub has_declared_type: bool,",
                "}",
            ]
        ),
        "\n".join(
            [
                "#[derive(Clone, Debug, Default, PartialEq)]",
                "struct __ZincFunctionMeta {",
                "    pub kind: String,",
                "    pub name: String,",
                "    pub fqn: String,",
                "    pub module_fqn: String,",
                "    pub file: String,",
                "    pub line_num: u32,",
                "    pub is_public: bool,",
                "    pub params: Vec<__ZincFunctionParameterMeta>,",
                "    pub return_type: __ZincTypeMeta,",
                "    pub is_async: bool,",
                "}",
            ]
        ),
        "\n".join(
            [
                "#[derive(Clone, Debug, Default, PartialEq)]",
                "struct __ZincBuiltinMeta {",
                "    pub kind: String,",
                "    pub name: String,",
                "    pub fqn: String,",
                "    pub module_fqn: String,",
                "    pub file: String,",
                "    pub line_num: u32,",
                "    pub is_public: bool,",
                "    pub params: Vec<__ZincFunctionParameterMeta>,",
                "    pub return_type: __ZincTypeMeta,",
                "    pub is_async: bool,",
                "}",
            ]
        ),
        "\n".join(
            [
                "#[derive(Clone, Debug, Default, PartialEq)]",
                "struct __ZincMethodMeta {",
                "    pub kind: String,",
                "    pub name: String,",
                "    pub fqn: String,",
                "    pub module_fqn: String,",
                "    pub file: String,",
                "    pub line_num: u32,",
                "    pub is_public: bool,",
                "    pub params: Vec<__ZincMethodParameterMeta>,",
                "    pub return_type: __ZincTypeMeta,",
                "    pub is_async: bool,",
                "    pub is_static: bool,",
                "    pub is_declared: bool,",
                "}",
            ]
        ),
        "\n".join(
            [
                "#[derive(Clone, Debug, Default, PartialEq)]",
                "struct __ZincVariableMeta {",
                "    pub kind: String,",
                "    pub name: String,",
                "    pub fqn: String,",
                "    pub module_fqn: String,",
                "    pub file: String,",
                "    pub line_num: u32,",
                "    pub is_public: bool,",
                "    pub value_type: __ZincTypeMeta,",
                "    pub has_declared_type: bool,",
                "    pub is_mutated: bool,",
                "    pub is_shadow: bool,",
                "}",
            ]
        ),
        "\n".join(
            [
                "#[derive(Clone, Debug, Default, PartialEq)]",
                "struct __ZincConstMeta {",
                "    pub kind: String,",
                "    pub name: String,",
                "    pub fqn: String,",
                "    pub module_fqn: String,",
                "    pub file: String,",
                "    pub line_num: u32,",
                "    pub is_public: bool,",
                "    pub value_type: __ZincTypeMeta,",
                "    pub value_text: String,",
                "}",
            ]
        ),
        "\n".join(
            [
                "#[derive(Clone, Debug, PartialEq)]",
                "enum __ZincComponentOrder {",
                "    DepthFirst,",
                "    BreadthFirst,",
                "    Topological,",
                "}",
            ]
        ),
    ]
