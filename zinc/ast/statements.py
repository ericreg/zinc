"""Statement AST nodes for the Zinc compiler."""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Union

from .expressions import Expression
from .types import BaseType, type_to_rust


class AssignmentKind(Enum):
    """Kind of variable assignment."""

    DECLARATION = auto()  # First assignment: let mut x = ...
    REASSIGNMENT = auto()  # Same type reassignment: x = ...
    SHADOW = auto()  # Type change: let mut x = ...


class Statement(ABC):
    """Base class for all statement nodes."""

    @abstractmethod
    def render(self) -> str:
        """Generate Rust code for this statement."""
        pass


@dataclass
class VariableAssignment(Statement):
    """Variable assignment statement."""

    variable_name: str
    value: Union[Expression, str]  # Expression or raw string for backward compat
    kind: AssignmentKind
    needs_mut: bool = False

    def render(self) -> str:
        # Handle both Expression objects and raw strings
        if isinstance(self.value, str):
            value_code = self.value
        else:
            value_code = self.value.render_rust()

        if self.kind == AssignmentKind.REASSIGNMENT:
            return f"{self.variable_name} = {value_code};"
        else:
            # DECLARATION or SHADOW - both need 'let', with optional 'mut'
            mut = "mut " if self.needs_mut else ""

            # Special case for empty Vec needing type annotation
            from .expressions import ArrayLiteralExpr
            if isinstance(self.value, ArrayLiteralExpr):
                if self.value.array_info and self.value.array_info.is_vector:
                    if not self.value.elements:
                        elem = type_to_rust(self.value.array_info.element_type)
                        return f"let {mut}{self.variable_name}: Vec<{elem}> = Vec::new();"

            return f"let {mut}{self.variable_name} = {value_code};"


@dataclass
class PrintStatement(Statement):
    """Print statement."""

    arguments: list[Union[Expression, str]]  # Expression or raw string

    def render(self) -> str:
        if not self.arguments:
            return "println!();"

        # Get the first argument (format string)
        first_arg = self.arguments[0]
        if isinstance(first_arg, str):
            format_string = first_arg
        else:
            format_string = first_arg.render_rust()

        # Remove surrounding quotes if present
        if format_string.startswith('"') and format_string.endswith('"'):
            format_string = format_string[1:-1]
        elif format_string.startswith("'") and format_string.endswith("'"):
            format_string = format_string[1:-1]

        # Extract expressions from {expr} patterns
        # Match both simple vars {var} and indexed access {var[index]}
        expr_pattern = r"\{([^}]+)\}"
        expressions = re.findall(expr_pattern, format_string)

        # If there are expressions, render as println! with format args
        if expressions:
            # Replace {expr} with {} for Rust's println! macro
            rust_format_string = re.sub(expr_pattern, "{}", format_string)
            args_str = f'"{rust_format_string}"'
            # Add the expressions as additional arguments
            for expr in expressions:
                args_str += f", {expr}"
            return f"println!({args_str});"
        else:
            # No expressions, just a plain string
            return f'println!("{format_string}");'


@dataclass
class ExpressionStatement(Statement):
    """Standalone expression (e.g., function call)."""

    expression: Expression

    def render(self) -> str:
        return f"{self.expression.render_rust()};"


@dataclass
class IfBranch:
    """A single if/else-if branch with condition and body."""

    condition: Expression
    body: list["Statement"]


@dataclass
class IfStatement(Statement):
    """If/else statement."""

    branches: list[IfBranch]  # if and else-if branches (each has condition)
    else_body: Optional[list["Statement"]] = None  # optional else block

    def render(self) -> str:
        lines = []
        for i, branch in enumerate(self.branches):
            keyword = "if" if i == 0 else "} else if"
            cond = branch.condition.render_rust()
            lines.append(f"{keyword} {cond} {{")
            for stmt in branch.body:
                # Handle multi-line statements (like nested if)
                stmt_lines = stmt.render().split("\n")
                for stmt_line in stmt_lines:
                    lines.append(f"    {stmt_line}")

        if self.else_body:
            lines.append("} else {")
            for stmt in self.else_body:
                stmt_lines = stmt.render().split("\n")
                for stmt_line in stmt_lines:
                    lines.append(f"    {stmt_line}")

        lines.append("}")
        return "\n".join(lines)


@dataclass
class Parameter:
    """Function parameter."""

    name: str
    type_annotation: Optional[str] = None
    resolved_type: Optional[str] = None  # Resolved type from monomorphization


@dataclass
class FunctionDeclaration(Statement):
    """Function declaration."""

    name: str
    parameters: list[Parameter]
    body: list["Statement"]
    return_type: Optional[str] = None
    mangled_name: Optional[str] = None  # Monomorphized function name
    is_template: bool = False  # True if this is an untyped template (don't render)
    is_async: bool = False  # True if called via spawn (becomes async fn)

    def render(self) -> str:
        # Skip rendering templates (they get monomorphized)
        if self.is_template:
            return ""

        # Use mangled name if available
        func_name = self.mangled_name if self.mangled_name else self.name

        # Build parameter list with resolved types
        param_strs = []
        for p in self.parameters:
            if p.resolved_type:
                param_strs.append(f"{p.name}: {p.resolved_type}")
            elif p.type_annotation:
                param_strs.append(f"{p.name}: {p.type_annotation}")
            else:
                param_strs.append(p.name)
        params = ", ".join(param_strs)

        # Add return type if known
        ret_type = f" -> {self.return_type}" if self.return_type else ""

        # Handle async functions
        async_kw = "async " if self.is_async else ""

        lines = [f"{async_kw}fn {func_name}({params}){ret_type} {{"]
        for stmt in self.body:
            for line in stmt.render().split("\n"):
                lines.append(f"    {line}")
        lines.append("}")
        return "\n".join(lines)


@dataclass
class ReturnStatement(Statement):
    """Return statement."""

    value: Optional[Expression] = None

    def render(self) -> str:
        if self.value:
            return f"return {self.value.render_rust()};"
        return "return;"


@dataclass
class SpawnStatement(Statement):
    """Spawn statement for concurrent execution."""

    call_expr: Expression  # The function call to spawn

    def render(self) -> str:
        call = self.call_expr.render_rust()
        return f"tokio::spawn({call});"


@dataclass
class ChannelSendStatement(Statement):
    """Channel send statement: sender <- value."""

    channel_name: str  # Variable name of the sender
    value: Expression
    is_bounded: bool = False  # Bounded channels need .await on send

    def render(self) -> str:
        val = self.value.render_rust()
        if self.is_bounded:
            # Bounded Sender::send() is async - needs .await
            return f"{self.channel_name}.send({val}).await.unwrap();"
        else:
            # UnboundedSender::send() is not async, it returns Result directly
            return f"{self.channel_name}.send({val}).unwrap();"


@dataclass
class ChannelDeclaration(Statement):
    """Channel creation with destructuring: let (tx, rx) = chan()."""

    base_name: str  # Original variable name (e.g., "x_chan")
    sender_name: str  # Derived sender name
    receiver_name: str  # Derived receiver name
    is_bounded: bool
    capacity: Optional[Expression] = None
    channel_info: Optional["ChannelTypeInfo"] = None  # Reference to shared channel info

    def render(self) -> str:
        from .types import ChannelTypeInfo
        elem_type = self.channel_info.element_type if self.channel_info else BaseType.UNKNOWN
        elem = type_to_rust(elem_type)

        if self.is_bounded:
            cap = self.capacity.render_rust() if self.capacity else "32"
            return f"let ({self.sender_name}, mut {self.receiver_name}) = tokio::sync::mpsc::channel::<{elem}>({cap});"
        return f"let ({self.sender_name}, mut {self.receiver_name}) = tokio::sync::mpsc::unbounded_channel::<{elem}>();"


@dataclass
class MethodCallStatement(Statement):
    """Standalone method call: b.push(10)."""

    target: Expression
    method_name: str
    arguments: list[Expression]

    def render(self) -> str:
        args = ", ".join(arg.render_rust() for arg in self.arguments)
        return f"{self.target.render_rust()}.{self.method_name}({args});"


@dataclass
class ForStatement(Statement):
    """For-in loop statement."""

    loop_variable: str
    iterable: Expression
    body: list["Statement"]

    def render(self) -> str:
        from .expressions import RangeExpr

        if isinstance(self.iterable, RangeExpr):
            # Ranges are consumed, no & needed
            iter_code = self.iterable.render_rust()
        else:
            # Collections: iterate by reference to avoid consuming
            iter_code = f"&{self.iterable.render_rust()}"

        lines = [f"for {self.loop_variable} in {iter_code} {{"]
        for stmt in self.body:
            stmt_lines = stmt.render().split("\n")
            for stmt_line in stmt_lines:
                lines.append(f"    {stmt_line}")
        lines.append("}")
        return "\n".join(lines)
