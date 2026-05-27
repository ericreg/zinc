"""Rust-style numeric literal helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass

from zinc.ast.types import BaseType, default_exact_type

INTEGER_SUFFIXES = ("u8", "i8", "u16", "i16", "u32", "i32", "u64", "i64", "u128", "i128", "usize", "isize")
FLOAT_SUFFIXES = ("f32", "f64")
INTEGER_SUFFIX_SET = set(INTEGER_SUFFIXES)
FLOAT_SUFFIX_SET = set(FLOAT_SUFFIXES)
NUMERIC_SUFFIXES = tuple(sorted(INTEGER_SUFFIXES + FLOAT_SUFFIXES, key=len, reverse=True))


@dataclass(frozen=True)
class NumericLiteral:
    """Parsed metadata for a Rust-style number literal."""

    base_type: BaseType
    exact_type: str | None
    value: int | float


def _strip_suffix(text: str) -> tuple[str, str | None]:
    """Strip a recognized Rust numeric suffix, leaving any separator underscore in the stem."""
    for suffix in NUMERIC_SUFFIXES:
        if text.endswith(suffix):
            return text[: -len(suffix)], suffix
    return text, None


def _clean_digits(text: str) -> str:
    """Remove visual separators from the numeric body."""
    return text.replace("_", "")


def _is_decimal_float_body(stem: str) -> bool:
    """Return True when an unsuffixed body is a decimal float form."""
    if stem.endswith("."):
        return True
    return "." in stem or bool(re.search(r"[eE]", stem))


def _integer_value(stem: str) -> int:
    """Parse an integer stem with Rust radix prefixes and ignored underscores."""
    cleaned = _clean_digits(stem)
    if cleaned.startswith(("0b", "0B")):
        return int(cleaned[2:], 2)
    if cleaned.startswith(("0o", "0O")):
        return int(cleaned[2:], 8)
    if cleaned.startswith(("0x", "0X")):
        return int(cleaned[2:], 16)
    return int(cleaned, 10)


def parse_numeric_literal(text: str) -> NumericLiteral | None:
    """Parse a Rust-style number literal, or return None for non-numeric literals."""
    stem, suffix = _strip_suffix(text)
    if not stem:
        return None

    if suffix in FLOAT_SUFFIX_SET:
        if stem.startswith(("0b", "0B", "0o", "0O", "0x", "0X")):
            return NumericLiteral(BaseType.INTEGER, default_exact_type(BaseType.INTEGER), _integer_value(text))
        return NumericLiteral(BaseType.FLOAT, suffix, float(_clean_digits(stem)))

    if suffix in INTEGER_SUFFIX_SET:
        return NumericLiteral(BaseType.INTEGER, suffix, _integer_value(stem))

    if _is_decimal_float_body(stem):
        return NumericLiteral(BaseType.FLOAT, default_exact_type(BaseType.FLOAT), float(_clean_digits(stem)))

    return NumericLiteral(BaseType.INTEGER, default_exact_type(BaseType.INTEGER), _integer_value(stem))


def is_numeric_literal(text: str) -> bool:
    """Return True when text is a parsed numeric literal."""
    try:
        return parse_numeric_literal(text) is not None
    except ValueError:
        return False


def numeric_literal_value(text: str) -> int | float:
    """Return the computed value for a numeric literal."""
    parsed = parse_numeric_literal(text)
    if parsed is None:
        raise ValueError(f"not a numeric literal: {text}")
    return parsed.value
