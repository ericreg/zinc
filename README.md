# Zinc

Zinc is a modern programming language that compiles to Rust. It combines Go-like concurrency primitives with dynamic typing, type inference, and object-oriented programming through structs.

## Key Features

- **Compiles to Rust** - Leverages Rust's performance, safety, and ecosystem
- **Go-style Concurrency** - Channels and `spawn` for easy concurrent programming
- **Python-style Dynamic Typing** - Variables can be reassigned to different types
- **Type Inference** - No explicit type annotations required
- **Strict Type Annotations** - Any written type annotation is enforced at compile time
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

### Variables & Dynamic Typing

Variables are declared by assignment. The same variable can be reassigned to different types:

```rust
fn main() {
    x = 1           // integer
    x = 3.14        // reassign to float
    x = "hello"     // reassign to string
    x = true        // reassign to boolean
    print("{x}")
}
```

If you want a local binding to stay fixed, annotate it directly. Typed locals are
strictly enforced:

```zinc
fn main() {
    x: i32 = 5
    x = 4      // ok
    // x = 3.0 // compile-time error
}
```

### Functions

Functions are declared with `fn`. Parameters don't require type annotations - the compiler infers types through monomorphization:

```rust
fn add(a, b) {
    return a + b
}

fn main() {
    x = add(3, 5)       // add_i64_i64 is generated
    y = add(1.3, 1.5)   // add_f64_f64 is generated
    print("{x}")        // 8
    print("{y}")        // 2.8
}
```

The compiler creates specialized versions of functions based on the argument types at each call site.

Annotated parameters are strict contracts:

```zinc
fn add_i32(x: i32, y: i32) {
    return x + y
}
```

`add_i32(1, 2)` is valid, but passing an already-typed `i64` or a float is a
compile-time error.

### Control Flow

#### If/Else

Parentheses around conditions are optional:

```zinc
fn main() {
    x = 10

    if x > 5 {
        print("x is greater than 5")
    }

    if x > 15 {
        print("x is greater than 15")
    } else {
        print("x is not greater than 15")
    }

    if x > 20 {
        print("big")
    } else if x > 5 {
        print("medium")
    } else {
        print("small")
    }
}
```

`if` also works as an expression, following Rust-style rules:

```zinc
fn label(count) {
    return if count == 1 {
        "item"
    } else {
        "items"
    }
}
```

In expression position, conditions must be `bool`, only one branch is evaluated,
and a missing `else` is allowed only when the `if` resolves to unit or a
missing branch diverges:

```zinc
fn main() {
    debug = true
    result = if debug {
        print("debug")
    }
}
```

#### For Loops

Iterate over arrays with `for...in`:

```rust
fn main() {
    a = [1, 2, 3]

    for x in a {
        print("{x}")
    }
}
```

#### Match Expressions

Pattern matching with range support:

```rust
fn main() {
    age = 25

    match age {
        0..17 => {
            print("minor")
        },
        18..64 => {
            print("adult")
        },
        _ => {
            print("senior")
        }
    }
}
```

### Arrays and Vectors

Arrays are created with bracket syntax. They're automatically promoted to vectors when using `.push()`:

```rust
fn main() {
    // Fixed array
    a = [1, 2, 3]

    for x in a {
        print("{x}")
    }

    // Empty array promoted to vector with push
    b = []
    b.push(10)
    b.push(20)
    b.push(30)

    for y in b {
        print("{y}")
    }
}
```

### Structs

Structs support fields with default values, static methods, and instance methods:

```rust
struct Counter {
    count: 0      // field with default value
    step: 1

    // Static constructor (no self)
    fn new(initial, step) {
        return Counter { count: initial, step: step }
    }

    // Instance method - reads self (becomes &self in Rust)
    fn get_count() {
        return self.count
    }

    // Instance method - writes to self (becomes &mut self in Rust)
    fn increment() {
        self.count = self.count + self.step
    }

    // Instance method - writes to self
    fn reset() {
        self.count = 0
    }

    fn set_step(new_step) {
        self.step = new_step
    }
}

fn main() {
    counter = Counter.new(0, 5)

    print(counter.get_count())   // 0

    counter.increment()
    print(counter.get_count())   // 5

    counter.increment()
    print(counter.get_count())   // 10

    counter.set_step(10)
    counter.increment()
    print(counter.get_count())   // 20

    counter.reset()
    print(counter.get_count())   // 0
}
```

**Private Fields:** Prefix field names with `_` to make them private:

```rust
struct Person {
    _secret: "hidden"    // private field
    name: ""             // public field
}
```

### Concurrency

Zinc provides Go-style concurrency with channels and spawn.

#### Channels

Create channels with `chan()` (unbounded) or `chan(n)` (bounded with capacity n):

```rust
fn tx(x, send_x) {
    send_x <- x          // send value to channel
}

fn main() {
    // Create unbounded channel
    x_chan = chan()

    // Spawn a task that sends data
    spawn tx(42, x_chan)

    // Receive data from the channel
    x = <- x_chan
    print("{x}")         // 42
}
```

#### Spawn

Use `spawn` to run functions concurrently (compiles to `tokio::spawn`):

```rust
fn greet(x) {
    print("{x}")
}

fn main() {
    spawn greet(42)
    print("done")
}
```

#### Select

Handle multiple channel operations:

```zinc
select {
    case msg = <-messages {
        print("{msg}")
    }
    case work <- 1 {
        print("sent")
    }
    default {
        print("idle")
    }
}
```

### String Interpolation

Use `{expression}` inside strings for interpolation:

```rust
fn main() {
    name = "Alice"
    age = 30
    print("Name: {name}, Age: {age}")
}
```

### Constants

Define global constants with `const`:

```rust
const PI = 3.14159
const MAX_SIZE = 100

fn main() {
    area = PI * 5 * 5
    print("Area: {area}")
}
```

## Compilation Pipeline

Zinc uses a 3-pass compiler:

1. **Atlas (Pass 1)** - Reachability analysis starting from `main()`. Builds a call graph and discovers all reachable functions, structs, and constants.

2. **Symbol Resolution (Pass 2)** - Type inference and monomorphization. Creates specialized versions of generic functions based on argument types at call sites.

3. **Code Generation (Pass 3)** - Generates Rust code with proper type annotations, async/await for spawned functions, and Tokio channels.

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
