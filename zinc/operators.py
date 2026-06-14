"""Operator overloading helpers shared by Zinc analysis and codegen."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ASSIGNMENT_TO_BINARY_OPERATOR = {
    "+=": "+",
    "-=": "-",
    "*=": "*",
    "/=": "/",
    "%=": "%",
    "**=": "**",
    "&=": "&",
    "|=": "|",
    "^=": "^",
    "<<=": "<<",
    ">>=": ">>",
}

BINARY_OPERATOR_SYMBOLS = frozenset(
    {
        "+",
        "-",
        "/",
        "%",
        "<<",
        ">>",
        "&",
        "^",
        "|",
        "<",
        "<=",
        ">",
        ">=",
        "&&",
        "||",
    }
)
UNARY_OPERATOR_SYMBOLS = frozenset({"~"})
COMPARISON_OPERATOR_SYMBOLS = frozenset({"<", "<=", ">", ">="})
LOGICAL_OPERATOR_SYMBOLS = frozenset({"and", "or", "&&", "||"})
INDEX_OPERATOR_SYMBOL = "[]"
OVERLOADABLE_OPERATOR_SYMBOLS = BINARY_OPERATOR_SYMBOLS | UNARY_OPERATOR_SYMBOLS | frozenset({INDEX_OPERATOR_SYMBOL})
BOOL_RESULT_OPERATOR_SYMBOLS = COMPARISON_OPERATOR_SYMBOLS | frozenset({"&&", "||"})

_OPERATOR_SUFFIXES = {
    "+": "add",
    "-": "sub",
    "/": "div",
    "%": "rem",
    "<<": "shl",
    ">>": "shr",
    "&": "bitand",
    "^": "bitxor",
    "|": "bitor",
    "~": "bitnot",
    "<": "lt",
    "<=": "le",
    ">": "gt",
    ">=": "ge",
    "&&": "logical_and",
    "||": "logical_or",
    INDEX_OPERATOR_SYMBOL: "index",
}


@dataclass(frozen=True)
class ResolvedOperatorCall:
    """A resolved overloaded operator call for one expression or assignment."""

    operator: str
    owner_qualified_name: str
    method_name: str
    is_static: bool
    receiver_index: int | None = None


def operator_method_name(symbol: str) -> str:
    """Return the hidden Rust/Zinc method name for one overloaded operator."""
    suffix = _OPERATOR_SUFFIXES.get(symbol)
    if suffix is None:
        suffix = "custom_" + "_".join(f"{ord(char):x}" for char in symbol)
    if not suffix:
        suffix = "custom"
    return f"__zinc_op_{suffix}"


def function_is_operator(ctx) -> bool:
    """Return True when a function declaration uses `fn operator...` syntax."""
    function_name = getattr(ctx, "functionName", lambda: None)()
    return bool(function_name and function_name.operatorFunctionName())


def operator_symbol_from_function_ctx(ctx) -> str | None:
    """Extract the declared operator symbol from a function declaration."""
    function_name = getattr(ctx, "functionName", lambda: None)()
    if function_name is None:
        return None
    operator_name = function_name.operatorFunctionName()
    if operator_name is None:
        return None
    return normalize_operator_symbol(operator_name.operatorSymbol().getText())


def function_name_from_ctx(ctx) -> str:
    """Return a stable internal function/method name for a function declaration."""
    operator_symbol = operator_symbol_from_function_ctx(ctx)
    if operator_symbol is not None:
        return operator_method_name(operator_symbol)
    return ctx.functionName().IDENTIFIER().getText()


def function_display_name_from_ctx(ctx) -> str:
    """Return the user-facing declaration name."""
    operator_symbol = operator_symbol_from_function_ctx(ctx)
    if operator_symbol is not None:
        return f"operator{operator_symbol}"
    return function_name_from_ctx(ctx)


def normalize_operator_symbol(text: str) -> str:
    """Normalize parser text for multi-token operator spellings."""
    if text == "[]":
        return INDEX_OPERATOR_SYMBOL
    return text


def operator_kind(symbol: str) -> Literal["binary", "unary", "index", "custom"]:
    """Classify an operator declaration by syntax."""
    if symbol == INDEX_OPERATOR_SYMBOL:
        return "index"
    if symbol in BINARY_OPERATOR_SYMBOLS:
        return "binary"
    if symbol in UNARY_OPERATOR_SYMBOLS:
        return "unary"
    return "custom"


def operator_kind_for_declaration(
    symbol: str,
    *,
    is_static: bool,
    parameter_count: int,
) -> Literal["binary", "unary", "index", "custom"]:
    """Classify one operator declaration using arity where symbols overlap."""
    if symbol in BINARY_OPERATOR_SYMBOLS and symbol in UNARY_OPERATOR_SYMBOLS:
        if (is_static and parameter_count == 1) or (not is_static and parameter_count == 0):
            return "unary"
    return operator_kind(symbol)
