# Zinc

Zinc is a modern programming language that compiles to Rust. It combines Go-like concurrency primitives with dynamic typing, type inference, and object-oriented programming through structs.

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

## Language Guide

see [USER_GUIDE.md](./USER_GUIDE.md)


## TODO / Roadmap

- [x] Modules and imports
- [x] Dynamic variable rebinding
- [x] Monomorphized functions
- [x] Structs and Struct composition
- [x] Enums
- [x] Callables and function vars/args
- [x] Closure support
- [x] Channels, spawn, close, and select
- [x] Arrays (with list auto promotion) and Tuples
- [x] Associative collections: dict, set, sort_dict, sort_set
- [x] Multiline strings
- [x] Strict type annotations
- [x] Compile Time Metaprogramming
- [x] Pattern matching
- [x] Generic-emulation with `infer` and type constraints
- [x] String interpolation
- [x] Basic control flow: if/else, for loops, while loops, match expressions  
- [x] Error handling: `try`, `match`, `fail`
- [x] Modules and imports
- [ ] Decorators
- [x] Lambda expressions
- [ ] Bimaps
- [ ] Priority queues
- [ ] Even more tests
- [ ] mdbook documentation

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
uv run pytest -n autp
```

To regenerate rust source
```sh
uv run python test/test_compile.py --update-output
```
