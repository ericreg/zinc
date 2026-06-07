# Zinc Roadmap

## Current Tasks

- [] std/filesystem
- [] ray tracing example and compare to python, rust, c++
- [] write "Why Zinc?" docs to defend the design choices and explain the vision for the language

## Implemented core pillars

- [x] Modules and imports
- [x] Dynamic variable rebinding
- [x] Monomorphized functions
- [x] Structs with methods
- [x] Struct composition, forward and orthogonal
- [x] First-class callables
- [x] Channels, spawn, bounded channels, and select
- [x] Arrays, dicts, sets, tuples
- [x] Base types
- [x] Multiline strings
- [x] Closure support
- [x] Strict type annotations
- [x] Enums
- [x] Metaprogramming model
- [x] Component constraints (basically generics-lite)
- [x] Return type annotations
- [x] Type alternatives, i32 | f32, numeric is sugar for i32 | f32 | u8 | ...
- [x] Rust-like numerical literals
- [x] Default and named parameters
- [x] Argument matching
- [x] Bitwise operations
- [x] Multiple assignment, x, y, z = 1
- [x] Lambda expressions
- [x] Decorators
- [x] Basic Rust interop
- [] Advanced Rust interop (ownership/lifetimes/generics)
- [] ranges
- [] operator overloading

## Highest-priority language gaps
- [ ] Complete zinc stdlib
- more efficient/readable rust code generation
- write the compilers in Zinc
- - [] hvm backend

## Other Ideas
- [] Possibly have a decimal type based on [`fixed-num`](https://docs.rs/fixed-num/latest/fixed_num/)
- [] Consider auto-promoting container types to concurrent lock-free data structures based on usage
- [] hvm backend for automatic parallelization

## Docs 
- [] Why Zinc?
- [] Tutorial
- [] Expand the guide into a small book / better language reference

## Tooling and quality
- [ ] Add a formatter
- [ ] Write `galv` build CLI / or use cargo / (should probably be a rust package)
- [ ] Add breakpoint debugging
- [ ] Fuzz tests


## Benchmarks

Example programs benchmarks in the following languages
- C3
- Nim
- Zig
- C
- C++ (latest)
- Rust
- Python
- Java
- Typescript
- Julia
- go

Benchmarks should measure
- wallclock time
- memory
- allocations
- binary size

Use rust benchmarks to optimize rust codegen

## Example Applications
- [] raytracing in one weekend
- [] cli/ps1 todo app
- [] kalman filter
- [] webserver
- [] math benchmarks




## Currently (possibly forever) unsupported in Zinc

- locking primitives (mutex, semaphore, etc) (use channels / lock-free data structures)
- inheritance (use composition)
- macros (Do not use the dark arts)
- traits (Not needed)
- generics (Not needed)
- https://benchmarksgame-team.pages.debian.net/benchmarksgame/

