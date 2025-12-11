"""Statement AST nodes for the Zinc compiler."""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Union

from .expressions import Expression


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

        # Extract variable names from {var} patterns
        variables = re.findall(r"\{(\w+)\}", format_string)

        # If there are variables, render as println! with format args
        if variables:
            # Replace {var} with {} for Rust's println! macro
            rust_format_string = re.sub(r"\{\w+\}", "{}", format_string)
            args_str = f'"{rust_format_string}"'
            # Add the variables as additional arguments
            for var in variables:
                args_str += f", {var}"
            return f"println!({args_str});"
        else:
            # No variables, just a plain string
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
