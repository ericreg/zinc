# Zinc

Zinc is a research programming language that compiles to Rust. It combines Go-like concurrency primitives with dynamic typing, type inference, and object-oriented programming through structs. It is highly experimental and not intended for production use. It is primarily a playground for exploring language design and hopefully a source of ideas for other languages.

## Key Features

- **Compiles to Rust** - Leverages Rust's performance, safety, and ecosystem
- **Go-style Concurrency** - Channels and `spawn` for easy concurrent programming
- **Python-style Dynamic Typing** - Variables can be reassigned to different types
- **Strict Type Annotations** - Any written type annotation is enforced at compile time
- **Type Inference** - No explicit type annotations required
- **Monomorphization** - Generic functions are specialized at compile time
- **Rich Compile-Time Metadata** - Object-oriented programming with static and instance methods

## Getting Started

### Compiling a Program

```sh
# Compile to Rust
python -m zinc.main compile program.zn -o output.rs

# Print the AST
python -m zinc.main tree program.zn

# Syntax check only
python -m zinc.main check program.zn
```

Generated Rust that uses Zinc runtime features (channels, contexts, or compile-time metadata) must be built in a Cargo project with the internal runtime crate enabled for the features the compiler reports:

```toml
zinc-internal = { path = ".../rust_runtime/zinc-internal", default-features = false, features = ["channel"] }
```

## Roadmap

see [ROADMAP.md](./ROADMAP.md)

## Language Guide

See [Why Zinc?](./docs/why_zinc.md) for a high level overview of the language design and philosophy.

See [USER_GUIDE.md](./USER_GUIDE.md) for a basic tutorial and language reference.

## Development

### VSCode extension

The `zinc-lang` VSCode extension provides syntax highlighting. It is not available on the marketplace yet, but you can build and install it locally

```sh
npm install -g @vscode/vsce
cd extension/zinc-lang
vsce package --allow-missing-repository --skip-license && code --install-extension zinc-lang-0.0.1.vsix
```


### Regenerate ANTLR4 Parser

```sh
docker run -it -v /Users/eric/code/zinc/zinc/parser:/workspace zinc-dev /regen
```

If you use the vscode devcontainer, you may just run the `regen` command directly in the terminal.

### Running Tests

```sh
uv run pytest -n auto
```

To regenerate rust source
```sh
uv run python test/test_compile.py --update-output
```
