"""AST module for the Zinc compiler."""

from .types import BaseType, TypeInfo, parse_literal
from .expressions import (
    Expression,
    LiteralExpr,
    IdentifierExpr,
    BinaryExpr,
    UnaryExpr,
    ParenExpr,
    CallExpr,
)
from .statements import (
    Statement,
    AssignmentKind,
    VariableAssignment,
    PrintStatement,
    IfBranch,
    IfStatement,
    Parameter,
    FunctionDeclaration,
    ReturnStatement,
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
    "CallExpr",
    # Statements
    "Statement",
    "AssignmentKind",
    "VariableAssignment",
    "PrintStatement",
    "IfBranch",
    "IfStatement",
    "Parameter",
    "FunctionDeclaration",
    "ReturnStatement",
    # Symbols
    "Symbol",
    "Scope",
]
