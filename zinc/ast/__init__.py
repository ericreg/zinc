"""AST module for the Zinc compiler."""

from .types import BaseType, TypeInfo, parse_literal
from .expressions import (
    Expression,
    LiteralExpr,
    IdentifierExpr,
    BinaryExpr,
    UnaryExpr,
    ParenExpr,
)
from .statements import (
    Statement,
    AssignmentKind,
    VariableAssignment,
    PrintStatement,
    IfBranch,
    IfStatement,
)
from .symbols import Symbol, Scope

__all__ = [
    # Types
    "BaseType",
    "TypeInfo",
    "parse_literal",
    # Expressions
    "Expression",
    "LiteralExpr",
    "IdentifierExpr",
    "BinaryExpr",
    "UnaryExpr",
    "ParenExpr",
    # Statements
    "Statement",
    "AssignmentKind",
    "VariableAssignment",
    "PrintStatement",
    "IfBranch",
    "IfStatement",
    # Symbols
    "Symbol",
    "Scope",
]
