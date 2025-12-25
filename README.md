# Zinc

Zinc is a modern programming language that compiles to Rust. It combines Go-like concurrency primitives with dynamic typing, type inference, and object-oriented programming through structs.

## Key Features

- **Compiles to Rust** - Leverages Rust's performance, safety, and ecosystem
- **Go-style Concurrency** - Channels and `spawn` for easy concurrent programming
- **Dynamic Typing** - Variables can be reassigned to different types
- **Type Inference** - No explicit type annotations required
- **Monomorphization** - Generic functions are specialized at compile time
- **Structs with Methods** - Object-oriented programming with static and instance methods

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

### Control Flow

#### If/Else

Parentheses around conditions are optional:

```rust
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

```rust
loop {
    select {
        case await event1() {
            // handle event 1
        }
        case await event2() {
            // handle event 2
        }
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

- [x] Dynamic variable assignments
- [x] Functions with monomorphic overloading
- [x] Arithmetic expressions
- [x] If / else if / else
- [x] Channels (unbounded and bounded)
- [x] For loops
- [x] Arrays/lists
- [x] String interpolation
- [x] Constants
- [x] Structs/objects with methods
- [ ] Constant folding
- [ ] While loops
- [ ] Maps
- [ ] Sets
- [ ] Error handling
- [ ] Modules and imports
- [ ] A ton of tests
- [ ] Tiny book documentation

## Development

### Regenerate ANTLR4 Parser

```sh
docker run -it -v /Users/eric/code/zinc/zinc/parser:/workspace zinc-dev /regen
```

### Running Tests

```sh
python -m pytest test/test_compile.py
```

## Project Structure

```
zinc/
├── zinc/                    # Compiler package
│   ├── parser/              # ANTLR4 generated parser
│   │   └── zinc.g4          # Grammar definition
│   ├── ast/                 # AST node definitions
│   │   └── types.py         # Type system
│   ├── main.py              # CLI entry point
│   ├── atlas.py             # Pass 1: Reachability analysis
│   ├── symbols.py           # Pass 2: Symbol resolution
│   └── codegen.py           # Pass 3: Rust code generation
├── test/
│   ├── zinc_source/         # Test programs (.zn files)
│   ├── rust_source/         # Expected Rust output
│   └── output/              # Expected execution output
└── README.md
```
