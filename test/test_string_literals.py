"""Focused unit tests for Zinc string-literal helpers."""

from zinc.string_literals import (
    decode_string_literal,
    is_interpolated_string_literal,
    is_string_literal,
    to_rust_string_literal,
)


def test_raw_string_decodes_multiline_and_doubled_backticks() -> None:
    """Raw strings keep exact contents except doubled backticks collapse to one."""
    literal = "`line 1\nline 2\npath: c:\\tmp\nliteral tick: ```"

    assert decode_string_literal(literal) == "line 1\nline 2\npath: c:\\tmp\nliteral tick: `"


def test_string_literal_detection_covers_all_supported_spellings() -> None:
    """Quoted and raw Zinc strings should all classify as string literals."""
    assert is_string_literal('"hello"')
    assert is_string_literal("'hello'")
    assert is_string_literal("`hello`")
    assert not is_string_literal("hello")


def test_only_double_quoted_strings_trigger_interpolation_lowering() -> None:
    """Raw strings keep braces literal instead of invoking interpolation."""
    assert is_interpolated_string_literal('"{name}"')
    assert not is_interpolated_string_literal("'{name}'")
    assert not is_interpolated_string_literal("`{name}`")


def test_non_double_quoted_strings_lower_to_valid_rust_strings() -> None:
    """Raw and single-quoted Zinc strings should become Rust string literals."""
    assert to_rust_string_literal("'hello'") == 'r"hello"'
    assert to_rust_string_literal("`hello`") == 'r"hello"'
    assert to_rust_string_literal('`say "hi" and "#`').startswith('r##"')
