# Change Log

All notable changes to the "zinc-lang" extension will be documented in this file.

Check [Keep a Changelog](http://keepachangelog.com/) for recommendations on how to structure this file.

## [Unreleased]

- Initial release
- Added syntax highlighting support for struct composition headers like `[A | B]` and `[A, B]`, including qualified composition paths.
- Added explicit primitive-type highlighting for `i8`, `i16`, `i128`, `u8`, `u16`, `u32`, `u64`, `u128`, `f8`, `f16`, and `f128`.
- Added syntax highlighting support for anonymous struct literals and anonymous struct type annotations using `struct { ... }`.
- Added raw backtick string highlighting for multiline string literals, including doubled-backtick escapes.
- Fixed raw string termination when a multiline backtick string ends after an escaped literal backtick.
- Added syntax highlighting support for type alternatives like `i32 | f32` and the `numeric` type constraint shorthand.
- Added syntax highlighting support for Rust interop syntax: `extern rust`, Rust `use` paths, opaque extern `type`, and `impl` declarations.
