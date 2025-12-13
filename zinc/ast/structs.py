"""Struct AST nodes for the Zinc compiler."""

import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, TYPE_CHECKING

from .expressions import Expression
from .statements import Statement, Parameter
from .types import BaseType, TypeInfo, type_to_rust


class FieldModifier(Enum):
    """Field modifier."""

    NONE = auto()  # Regular mutable field
    CONST = auto()  # Immutable after initialization


@dataclass
class StructField:
    """A field in a struct definition."""

    name: str
    type_annotation: Optional[str] = None  # Explicit type (e.g., "i32", "string")
    default_value: Optional[Expression] = None  # Default value expression
    modifier: FieldModifier = FieldModifier.NONE
    resolved_type: Optional[BaseType] = None  # Inferred/resolved type

    @property
    def is_private(self) -> bool:
        """Fields starting with _ are private."""
        return self.name.startswith("_")

    @property
    def is_const(self) -> bool:
        return self.modifier == FieldModifier.CONST

    def rust_type(self) -> str:
        """Get Rust type for this field."""
        if self.resolved_type:
            return type_to_rust(self.resolved_type)
        if self.type_annotation:
            return zinc_type_to_rust(self.type_annotation)
        return "unknown"

    def rust_default(self) -> str:
        """Get Rust default value for this field."""
        if self.default_value:
            return self.default_value.render_rust()
        # Zero-initialize based on type
        return zero_value_for_type(self.resolved_type or BaseType.UNKNOWN)


@dataclass
class StructMethod:
    """A method in a struct definition."""

    name: str
    parameters: list["Parameter"]
    body: list["Statement"]
    return_type: Optional[str] = None
    is_static: bool = False  # True if no self usage
    self_mutability: Optional[str] = None  # None, "&self", or "&mut self"
    is_template: bool = False  # True if untyped parameters

    def render(self, struct_name: str) -> str:
        """Generate Rust code for this method."""
        # Build parameter list
        param_strs = []
        if not self.is_static:
            param_strs.append(self.self_mutability or "&self")

        for p in self.parameters:
            if p.resolved_type:
                param_strs.append(f"{p.name}: {p.resolved_type}")
            elif p.type_annotation:
                param_strs.append(f"{p.name}: {p.type_annotation}")
            else:
                param_strs.append(p.name)
        params = ", ".join(param_strs)

        # Return type
        ret_type = f" -> {self.return_type}" if self.return_type else ""

        lines = [f"fn {self.name}({params}){ret_type} {{"]
        for stmt in self.body:
            for line in stmt.render().split("\n"):
                lines.append(f"    {line}")
        lines.append("}")
        return "\n".join(lines)


@dataclass
class StructDeclaration(Statement):
    """Struct type declaration."""

    name: str
    fields: list[StructField] = field(default_factory=list)
    methods: list[StructMethod] = field(default_factory=list)

    def render(self) -> str:
        """Generate Rust struct and impl block."""
        lines = []

        # Struct definition
        lines.append(f"struct {self.name} {{")
        for f in self.fields:
            vis = "" if f.is_private else "pub "
            rust_type = f.rust_type()
            lines.append(f"    {vis}{f.name}: {rust_type},")
        lines.append("}")
        lines.append("")

        # Impl block
        if self.methods:
            lines.append(f"impl {self.name} {{")
            for method in self.methods:
                method_code = method.render(self.name)
                for line in method_code.split("\n"):
                    lines.append(f"    {line}")
                lines.append("")
            lines.append("}")

        return "\n".join(lines)


@dataclass
class StructInstantiationExpr(Expression):
    """Struct literal instantiation: MyStruct { a: 1, b: 2 }."""

    struct_name: str
    field_inits: dict[str, Expression] = field(default_factory=dict)
    type_info: Optional[TypeInfo] = None
    struct_decl: Optional[StructDeclaration] = None  # Reference to struct definition

    def render_rust(self) -> str:
        from .expressions import LiteralExpr

        lines = [f"{self.struct_name} {{"]

        # If we have struct_decl, include all fields with defaults
        if self.struct_decl:
            for f in self.struct_decl.fields:
                if f.name in self.field_inits:
                    field_value = self.field_inits[f.name]
                    # Convert string literals to String::from() for String fields
                    if (f.rust_type() == "String" and
                        isinstance(field_value, LiteralExpr) and
                        field_value.type_info and
                        field_value.type_info.base == BaseType.STRING):
                        value = field_value.render_rust_as_string()
                    else:
                        value = field_value.render_rust()
                else:
                    value = f.rust_default()
                lines.append(f"    {f.name}: {value},")
        else:
            # No struct decl, just render provided fields
            for name, value in self.field_inits.items():
                lines.append(f"    {name}: {value.render_rust()},")

        lines.append("}")
        return "\n".join(lines)


@dataclass
class SelfExpr(Expression):
    """Reference to self in instance methods."""

    type_info: Optional[TypeInfo] = None

    def render_rust(self) -> str:
        return "self"


@dataclass
class MemberAccessExpr(Expression):
    """Field or method access: obj.field or obj.method."""

    target: Expression
    member: str
    type_info: Optional[TypeInfo] = None

    def render_rust(self) -> str:
        return f"{self.target.render_rust()}.{self.member}"


@dataclass
class StaticMethodCallExpr(Expression):
    """Static method call: MyStruct.method(args) or Self::method(args)."""

    struct_name: str
    method_name: str
    arguments: list[Expression] = field(default_factory=list)
    type_info: Optional[TypeInfo] = None
    struct_decl: Optional["StructDeclaration"] = None  # Reference to struct definition

    def render_rust(self) -> str:
        from .expressions import LiteralExpr

        args_rendered = []
        for i, arg in enumerate(self.arguments):
            # Check if we should convert string literal to String::from()
            if self.struct_decl:
                method = next((m for m in self.struct_decl.methods if m.name == self.method_name), None)
                if method and i < len(method.parameters):
                    param = method.parameters[i]
                    param_type = param.resolved_type or param.type_annotation
                    if (param_type == "String" and
                        isinstance(arg, LiteralExpr) and
                        arg.type_info and
                        arg.type_info.base == BaseType.STRING):
                        args_rendered.append(arg.render_rust_as_string())
                        continue
            args_rendered.append(arg.render_rust())

        args = ", ".join(args_rendered)
        return f"{self.struct_name}::{self.method_name}({args})"


# Helper functions

KNOWN_TYPES = {"i32", "i64", "f32", "f64", "string", "bool", "String"}


def is_known_type(identifier: str) -> bool:
    """Check if an identifier is a known type name."""
    return identifier.lower() in {t.lower() for t in KNOWN_TYPES}


def zinc_type_to_rust(zinc_type: str) -> str:
    """Convert Zinc type name to Rust."""
    mapping = {
        "i32": "i32",
        "i64": "i64",
        "f32": "f32",
        "f64": "f64",
        "string": "String",
        "bool": "bool",
    }
    return mapping.get(zinc_type.lower(), zinc_type)


def zinc_type_to_base(zinc_type: str) -> BaseType:
    """Convert Zinc type name to BaseType."""
    mapping = {
        "i32": BaseType.INTEGER,
        "i64": BaseType.INTEGER,
        "f32": BaseType.FLOAT,
        "f64": BaseType.FLOAT,
        "string": BaseType.STRING,
        "bool": BaseType.BOOLEAN,
    }
    return mapping.get(zinc_type.lower(), BaseType.UNKNOWN)


def zero_value_for_type(base_type: BaseType) -> str:
    """Get zero value for a type."""
    mapping = {
        BaseType.INTEGER: "0",
        BaseType.FLOAT: "0.0",
        BaseType.STRING: "String::new()",
        BaseType.BOOLEAN: "false",
    }
    return mapping.get(base_type, "Default::default()")
