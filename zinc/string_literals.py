"""Utilities for Zinc string-literal classification and lowering."""

from __future__ import annotations

import ast


def is_raw_string_literal(text: str) -> bool:
    """Return True when the Zinc literal uses C3-style backticks."""
    return len(text) >= 2 and text[0] == "`" and text[-1] == "`"


def is_quoted_string_literal(text: str) -> bool:
    """Return True when the Zinc literal uses single or double quotes."""
    return len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'"}


def is_string_literal(text: str) -> bool:
    """Return True for any Zinc string literal spelling."""
    return is_raw_string_literal(text) or is_quoted_string_literal(text)


def is_interpolated_string_literal(text: str) -> bool:
    """Return True for double-quoted Zinc strings that need interpolation lowering."""
    return len(text) >= 2 and text[0] == text[-1] == '"' and "{" in text


def decode_string_literal(text: str) -> str:
    """Decode a Zinc string literal into its runtime contents."""
    if is_raw_string_literal(text):
        return text[1:-1].replace("``", "`")
    if is_quoted_string_literal(text):
        decoded = ast.literal_eval(text)
        if not isinstance(decoded, str):
            raise ValueError(f"Expected string literal: {text}")
        return decoded
    raise ValueError(f"Unknown string literal form: {text}")


def to_rust_raw_string(value: str) -> str:
    """Render a Python string as a Rust raw string literal with safe delimiters."""
    hashes = ""
    while f'"{hashes}' in value:
        hashes += "#"
    return f'r{hashes}"{value}"{hashes}'


def to_rust_string_literal(text: str) -> str:
    """Render a Zinc string literal as a Rust string literal."""
    if is_raw_string_literal(text):
        return to_rust_raw_string(decode_string_literal(text))
    if is_quoted_string_literal(text):
        if text[0] == '"':
            return text
        return to_rust_raw_string(decode_string_literal(text))
    raise ValueError(f"Unknown string literal form: {text}")
