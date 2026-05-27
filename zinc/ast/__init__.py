"""AST module for the Zinc compiler."""

from .expressions import (
    BinaryExpr,
    CallExpr,
    Expression,
    IdentifierExpr,
    LiteralExpr,
    ParenExpr,
    UnaryExpr,
)
from .statements import (
    AssignmentKind,
    FunctionDeclaration,
    IfBranch,
    IfStatement,
    Parameter,
    PrintStatement,
    ReturnStatement,
    Statement,
    VariableAssignment,
)
from .symbols import Scope, Symbol
from .types import BaseType, TypeInfo, parse_literal

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
