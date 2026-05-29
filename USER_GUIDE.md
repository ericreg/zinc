# Zinc User Guide

Zinc is a small programming language that compiles to Rust. Its surface syntax is
intended to feel lightweight: variables are declared by assignment, most types are
inferred, functions are monomorphized at compile time, and concurrency uses
channel and `spawn` primitives.

This guide describes the language as implemented by the current compiler and
test suite.

## Running Zinc

Compile a Zinc source file to Rust:

```sh
python -m zinc.main compile program.zn -o output.rs
```

Print the parse tree:

```sh
python -m zinc.main tree program.zn
```

Check syntax and compiler diagnostics without writing Rust:

```sh
python -m zinc.main check program.zn
```

A Zinc program normally starts at `fn main()`.

```zinc
fn main() {
    print("hello from Zinc")
}
```

Statements do not use semicolons.

Zinc supports line comments and block comments:

```zinc
// line comment

/*
block comment
*/
```

## Import Statements

Zinc v1 modules are package-scoped and file-backed. Every package root must
contain a `pkg.toml` file:

```toml
[package]
name = "my_pkg"
version = "0.1.0"
```

Import paths are slash-separated and package-relative. `import foo/bar`
resolves to `foo/bar.zn` under the package root.

Supported forms:

```zinc
import math/vectors
import math/vectors as vec
import std/io [File, String]
```

Bare imports inject all public top-level `fn`, `struct`, and `const`
declarations from the target module. Alias imports bind a module namespace that
is accessed with `.`:

```zinc
import modules/_lib/io as io

fn main() {
    file = io.File { name: "notes" }
    print(io.size())
    print("{io.TAG}")
}
```

Selective imports inject only the listed public names:

```zinc
import geometry/shapes [Point, make_origin]
```

Top-level names starting with `_` are private to their module. Cyclic imports,
missing modules, unknown selective imports, and duplicate imported names are
compile errors.

## Values And Variables

Variables are declared by assignment:

```zinc
fn main() {
    count = 3
    name = "Ada"
    ready = true

    print("{name}")
}
```

The compiler infers types from values and usage. A name can be rebound in a new
scope or later assignment:

```zinc
fn main() {
    value = 1
    value = 2.5
    value = "now a string"

    print("{value}")
}
```

Primitive values include:

- integers, inferred as Zinc integer values and usually lowered to Rust `i64`
- floats, lowered to Rust `f64`
- strings
- booleans

Integer literals can also use hexadecimal, octal, or binary notation:

```zinc
fn main() {
    hex = 0xff
    octal = 0o77
    binary = 0b1010

    print("{hex}")
    print("{octal}")
    print("{binary}")
}
```

## Strings And Printing

Use `print(...)` to write a line to stdout:

```zinc
fn main() {
    print("plain text")
    print(42)
}
```

Strings support interpolation with `{expression}`:

```zinc
fn main() {
    name = "Ada"
    score = 99

    print("{name}: {score}")
    print("next score: {score + 1}")
}
```

Use double-quoted strings in Zinc source when you want interpolation or normal escape
processing.

Use backtick raw strings when you want multiline text or exact contents with no
escape processing:

```zinc
fn main() {
    note = `line 1
line 2
literal braces: {name}
literal slash: \tmp`

    tick = `backtick: ````

    print(note)
    print(tick)
}
```

Raw strings follow C3-style backtick rules:

- they may span multiple lines
- backslashes are not escapes
- `{...}` stays literal and does not interpolate
- write a literal backtick as `` ``

## Operators

Arithmetic:

```zinc
fn main() {
    a = 10 + 2
    b = 10 - 2
    c = 10 * 2
    d = 10 / 2
    e = 10 % 3
}
```

Comparison:

```zinc
fn main() {
    print(1 < 2)
    print(1 <= 2)
    print(1 > 2)
    print(1 >= 2)
    print(1 == 2)
    print(1 != 2)
}
```

Boolean logic:

```zinc
fn main() {
    a = true and false
    b = true or false
    c = !false
    d = not false

    print("{a}")
    print("{b}")
    print("{c}")
    print("{d}")
}
```

Integer bitwise operations use Rust-like spelling:

```zinc
fn main() {
    mask: u8 = 0b1010
    flags: u8 = 0b1100

    print(mask & flags)
    print(mask | flags)
    print(mask ^ flags)
    print(!mask)
    print(mask << 1)
    print(flags >> 2)
}
```

`&`, `|`, `^`, `<<`, and `>>` are integer-only. Use `and`, `or`, `&&`,
`||`, `not`, or `!` for boolean logic.

Mixed integer and float arithmetic promotes to float:

```zinc
fn main() {
    value = 1 + 2.5
    print("{value}") // 3.5
}
```

## Functions

Functions are declared with `fn`:

```zinc
fn add(a, b) {
    return a + b
}

fn main() {
    print(add(2, 3))
    print(add(1.5, 2.5))
}
```

Function parameter and return types are inferred. Generic-looking functions are
monomorphized: the compiler creates specialized Rust functions for each concrete
set of argument types used by reachable call sites.

Functions can return early:

```zinc
fn first_positive(values) {
    for value in values {
        if value > 0 {
            return value
        }
    }

    return 0
}
```

Parameters can optionally use type annotations where the compiler supports an
annotated position:

```zinc
fn double(x: i64) {
    return x * 2
}
```

Common annotation names include `i32`, `i64`, `f32`, `f64`, `string`, and `bool`.

Annotations are enforced as compile-time contracts. They are not optional hints.
This also applies to local bindings:

```zinc
fn main() {
    x: i32 = 5
    x = 4      // ok
    // x = 4.0 // compile-time error
}
```

## Callables And Lambdas

Functions and lambdas can be stored, passed, returned, and called through the
same `value(args...)` syntax:

```zinc
fn apply(f, x) {
    return f(x)
}

fn main() {
    inc = x -> x + 1
    print(apply(inc, 4))
    print(apply(x -> x * 2, 5))
}
```

Arrow lambdas are expression-only. Use `fn(...) { ... }` when a closure needs
multiple statements:

```zinc
fn main() {
    f = fn(x) {
        y = x + 1
        return y * 2
    }
}
```

Arrow lambdas support one untyped bare parameter, parenthesized parameter lists,
zero parameters, and partial annotations:

```zinc
x -> x + 1
(x, y) -> x + y
(x, y: i32) -> x + 1
() -> 42
```

## Constants

Global constants use `const`:

```zinc
const MAX_RETRIES = 3
const APP_NAME = "worker"

fn main() {
    print("{APP_NAME}")
    print("{MAX_RETRIES}")
}
```

## Control Flow

### If And Else

Conditions do not require parentheses:

```zinc
fn main() {
    x = 10

    if x > 20 {
        print("large")
    } else if x > 5 {
        print("medium")
    } else {
        print("small")
    }
}
```

`if` is also an expression, so you can use it anywhere Zinc expects a value:

```zinc
fn label(count) {
    return if count == 1 {
        "item"
    } else {
        "items"
    }
}
```

The expression form follows Rust-style rules:

- Conditions must resolve to `bool`.
- Only the selected branch is evaluated.
- `else` may be omitted only when the whole `if` resolves to unit or the
  missing branch would diverge with `return`, `break`, or `continue`.
- The branch value is the final expression in the branch block.

For example, this unit-valued `if` expression is valid:

```zinc
fn main() {
    debug = true
    result = if debug {
        print("debug")
    }
}
```

### Match

`match` supports literal patterns, wildcard `_`, bindings, tuple patterns,
struct patterns, and integer range patterns:

```zinc
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

Range patterns can be exclusive with `..` or inclusive with `..=`.

### For Loops

`for` iterates over ranges and iterable collections:

```zinc
fn main() {
    for n in 0..3 {
        print("{n}") // 0, 1, 2
    }

    for n in 1..=3 {
        print("{n}") // 1, 2, 3
    }
}
```

Named collections are iterated without consuming the collection, so they can be
used after the loop:

```zinc
fn main() {
    values = [2, 4, 6]
    total = 0

    for value in values {
        total = total + value
    }

    print("{total}")
    print("{values.len()}")
}
```

Loop variables are local bindings. Reassigning a loop variable affects only the
current iteration:

```zinc
fn main() {
    total = 0

    for x in 0..3 {
        x = x + 10
        total = total + x
    }

    print("{total}") // 33
}
```

### While

```zinc
fn main() {
    i = 0
    total = 0

    while i < 4 {
        total = total + i
        i = i + 1
    }

    print("{total}")
}
```

The condition is checked before each iteration.

### Loop, Break, And Continue

`loop` creates an infinite loop. Use `break` to exit:

```zinc
fn main() {
    i = 0

    loop {
        print("{i}")
        i = i + 1

        if i == 3 {
            break
        }
    }
}
```

`continue` skips to the next iteration of the innermost loop:

```zinc
fn main() {
    i = 0

    while i < 5 {
        i = i + 1

        if i == 2 {
            continue
        }

        print("{i}")
    }
}
```

## Arrays

Array literals use brackets:

```zinc
fn main() {
    values = [1, 2, 3]

    print("{values[0]}")
    print("{values.len()}")
}
```

Empty arrays are allowed only when later use gives them an element type:

```zinc
fn main() {
    values = []
    values.push(10)
    values.push(20)

    print("{values[1]}")
}
```

An empty array that is never constrained is a compile-time error:

```zinc
fn main() {
    values = []
    // error: cannot infer element type
}
```

Useful array operations:

- `values.push(value)`
- `values.len()`
- `values[index]`
- `for value in values { ... }`

## Tuples

Tuple literals use parentheses with commas:

```zinc
fn main() {
    pair = (7, "seven")
    triple = (1, 2, 3)
    single = ("only",)

    first = pair[0]
    second = pair[1]

    print("{first}")
    print("{second}")
}
```

`(x)` is a parenthesized expression, not a tuple. Use `(x,)` for a one-element
tuple.

Tuple indexes must be integer literals known at compile time. Out-of-bounds
indexes are compile-time errors.

```zinc
fn main() {
    pair = (10, 20)
    first = pair[0]
    print("{first}")

    // pair[2] is an error
}
```

Tuples can be destructured:

```zinc
fn main() {
    a, b = (2, 3)
    print("{a}")
    print("{b}")

    (name, score) = ("ada", 9)
    print("{name}: {score}")
}
```

Tuples can be function arguments and return values:

```zinc
fn sum_pair(pair) {
    return pair[0] + pair[1]
}

fn make_pair(seed) {
    return (seed, seed + 1)
}

fn main() {
    print(sum_pair((10, 20)))

    left, right = make_pair(4)
    print("{left}")
    print("{right}")
}
```

Arrays of tuples can be destructured in loops:

```zinc
fn main() {
    pairs = [(1, 2), (3, 4)]

    for a, b in pairs {
        print("{a}")
        print("{b}")
    }
}
```

## Dictionaries

Dictionaries map keys to values. Unordered dictionaries use `dict()` or dict
literals and compile to Rust `HashMap`.

```zinc
fn main() {
    scores = {"a": 1, "b": 2.5}

    first = scores["a"]
    second = scores.get("b")
    count = scores.len()

    print("{first}")
    print("{second}")
    print("{count}")
}
```

Use `dict()` for an empty dictionary:

```zinc
fn main() {
    scores = dict()
    scores["left"] = 10
    scores.insert("right", 20)

    right = scores.get("right")
    print("{right}")
}
```

The empty literal `{}` is rejected because it is ambiguous between a dictionary
and a set:

```zinc
fn main() {
    // scores = {} // error
    scores = dict()
}
```

Dictionary methods:

- `dict.insert(key, value)`
- `dict.get(key)`
- `dict.remove(key)`
- `dict.clear()`
- `dict.contains_key(key)`
- `dict.len()`
- `dict.is_empty()`
- `dict.keys()`
- `dict.values()`
- `dict.items()`

`dict[key]` and `dict.get(key)` both require the key to exist.

Dictionary values can promote mixed integer and float values to float:

```zinc
fn main() {
    scores = {"a": 1, "b": 2.5}
    first = scores.get("a")
    print("{first}")
}
```

In the current implementation, float dictionary keys are rejected because the
Rust collection types used by Zinc do not support plain `f64` keys.

## Sets

Sets hold unique values. Unordered sets use `set()` or set literals and compile
to Rust `HashSet`.

```zinc
fn main() {
    values = {1, 2, 3}
    has_two = values.contains(2)
    count = values.len()

    print("{has_two}")
    print("{count}")
}
```

Use `set()` for an empty set:

```zinc
fn main() {
    values = set()
    values.push(1)
    values.insert(2)
    has_two = values.contains(2)

    print("{has_two}")
}
```

Set methods:

- `set.push(value)` as an alias for insert
- `set.insert(value)`
- `set.remove(value)`
- `set.clear()`
- `set.contains(value)`
- `set.len()`
- `set.is_empty()`

Float set elements are rejected in the current implementation for the same
reason float dictionary keys are rejected.

## Sorted Dictionaries And Sets

Sorted collections use tree-backed Rust collections.

- `sort_dict()` compiles to `BTreeMap`
- `sort_set()` compiles to `BTreeSet`

Use sorted collections when iteration order matters:

```zinc
fn main() {
    scores = sort_dict()
    scores["b"] = 2
    scores["a"] = 1

    for key in scores.keys() {
        print("{key}") // a, then b
    }

    values = sort_set()
    values.insert(3)
    values.insert(1)
    values.insert(2)

    for value in values {
        print("{value}") // 1, then 2, then 3
    }
}
```

Unordered `dict()` and `set()` iteration order is unspecified.

## Dictionary Iteration

Bare dictionary iteration yields `(key, value)` items:

```zinc
fn main() {
    scores = sort_dict()
    scores["a"] = 1
    scores["b"] = 2

    for key, value in scores {
        print("{key}")
        print("{value}")
    }
}
```

This is equivalent to iterating `scores.items()`:

```zinc
fn main() {
    scores = sort_dict()
    scores["a"] = 1

    for (key, value) in scores.items() {
        print("{key}: {value}")
    }
}
```

You can also bind the item tuple directly:

```zinc
fn main() {
    scores = sort_dict()
    scores["a"] = 1

    for item in scores.items() {
        key = item[0]
        value = item[1]

        print("{key}")
        print("{value}")
    }
}
```

Dictionary iteration helpers:

```zinc
fn main() {
    scores = sort_dict()
    scores["a"] = 1
    scores["b"] = 2

    for key in scores.keys() {
        print("{key}")
    }

    for value in scores.values() {
        print("{value}")
    }

    for key, value in scores.items() {
        print("{key}: {value}")
    }
}
```

Dictionary iteration yields local owned values in this version of Zinc. Reassigning
loop variables does not mutate the dictionary:

```zinc
fn main() {
    scores = sort_dict()
    scores["a"] = 10

    for key, value in scores {
        key = "changed"
        value = value + 10
    }

    original = scores.get("a")
    print("{original}") // 10
}
```

Mutating a dictionary while iterating it is rejected.

## Structs

Structs group fields and methods:

```zinc
struct Point {
    x: i32
    y: i32
}

fn main() {
    p = Point { x: 10, y: 20 }

    print(p.x)
    print(p.y)
}
```

Fields can have explicit types or default values:

```zinc
struct Counter {
    count: 0
    step: 1
    name: string
}

fn main() {
    counter = Counter { name: "jobs" }

    print(counter.count)
    print(counter.step)
}
```

Anonymous structs are lightweight, data-only structural types. Use `struct { ... }`
in expression position to build a value, or in type position to require an exact
shape:

```zinc
fn area(rect: struct {
    width: i64
    height: i64
}) {
    return rect.width * rect.height
}

fn main() {
    rect = struct {
        height: 4
        width: 3
    }

    print(area(rect))
}
```

Anonymous structs use exact structural typing:

- field order does not matter
- extra or missing fields are errors
- anonymous structs only interoperate with other anonymous structs of the same shape
- named structs remain nominal and do not automatically interoperate with anonymous structs

Anonymous structs are data-only in v1: they do not declare methods, composition,
`const` fields, or privacy modifiers.

Fields whose names begin with `_` are private in generated Rust:

```zinc
struct User {
    _id: i32
    username: string
}
```

Struct fields can be `const`, which makes them set-once fields:

```zinc
struct Config {
    const max_retries: 3
    const api_version: string
    name: string
}

fn main() {
    cfg = Config {
        api_version: "v1"
        name: "service"
    }

    print(cfg.max_retries)
}
```

Methods are declared inside a struct. Methods that reference `self` become
instance methods. Methods that do not reference `self` become static methods.

```zinc
struct Counter {
    count: 0
    step: 1

    fn new(initial, step) {
        return Counter { count: initial, step: step }
    }

    fn get_count() {
        return self.count
    }

    fn increment() {
        self.count = self.count + self.step
    }
}

fn main() {
    counter = Counter.new(0, 5)

    counter.increment()
    print(counter.get_count())
}
```

## Enums

Enums support unit variants, payload variants, and methods:

```zinc
enum Status {
    Ready
    Busy { worker: string }

    fn label() {
        return "status"
    }
}

fn main() {
    ready = Status.Ready
    busy = Status.Busy { worker: "a" }

    match busy {
        Status.Ready => {
            print("ready")
        }
        Status.Busy { worker } => {
            print(worker)
        }
    }

    print(Status.label())
}
```

Enum methods follow the same rule as struct methods: touching `self` makes them
instance methods, otherwise they are static methods.

## Compile-Time Metadata

Zinc exposes compiler-known metadata as compile-time values:

- `meta(x)` returns symbol/declaration metadata
- `type(x)` returns concrete type metadata
- `line()` returns the current call-site line number
- `has_component(item, Component)` checks nominal recursive composition
- `implements(item, InterfaceLike)` checks the public instance API structurally

`meta(...)` only accepts named program entities such as variables, fields,
methods, functions, structs, enums, enum variants, consts, parameters, and
builtins. `meta(123)` is a compile-time error.

```zinc
const APP = "zinc"

struct Profile {
    name: string
}

fn main() {
    profile = Profile { name: "Ada" }

    print(meta(Profile).name)
    print(meta(profile.name).owner().name)
    print(meta(APP).value_type.name)
    print(line())
}
```

`type(...)` works on both value expressions and type symbols:

```zinc
fn main() {
    pair = (1, "two")

    print(type(i64).name)
    print(type(pair).kind)
    print(type(pair).args[1].name)
}
```

Channels expose a channel-specific type metadata shape. `type(channel_value)`
returns `ChannelMeta`, which behaves like `TypeMeta` with one extra public
field:

- `is_bounded: bool`

The channel payload type is stored in `args[0]`:

```zinc
fn main() {
    open = chan()
    open <- 1

    bounded = chan(2)
    bounded <- "hi"

    print(type(open).args[0].name)      // i64
    print(type(open).is_bounded)        // false
    print(type(bounded).args[0].name)   // String
    print(type(bounded).is_bounded)     // true
    print(type(type(open)).name)        // ChannelMeta
}
```

Struct and enum metadata also expose effective members:

```zinc
enum Color {
    Red
    Blue
}

struct Base {
    name: string
}

struct Detail {
    level: i64
}

struct Node [ Base | Detail ] {
    enabled: bool
}

fn main() {
    print(type(Node).fields())
    print(type(Node).methods())
    print(type(Node).components())
    print(type(Node).recursive_components())
    print(type(Color).variants())
}
```

## Compile-Time Constraints

`#[ ... ]` is reserved for compile-time constraint attributes. In v1, constraints
apply to untyped function parameters and `infer` struct fields.

Structs can infer field types at instantiation time:

```zinc
struct Point {
    x: infer
    y: infer
}

fn main() {
    p = Point { x: 1, y: 2 }
    print(type(p).name) // Point<i64, i64>
}
```

Constraints can restrict inferred types:

```zinc
#[
    x in [i64],
    type(y) in [type(string)],
]
struct Pair {
    x: infer
    y: infer
}
```

The short form:

```zinc
#[ x in [i64, f64] ]
```

desugars to:

```zinc
#[ type(x) in [type(i64), type(f64)] ]
```

Untyped parameters can use nominal or structural constraints:

```zinc
struct Shape {
    name: string
}

struct Shape2D [Shape] {
    fn area() {
        return 0
    }
}

#[has_component(shape, Shape2D)]
fn area_nominal(shape) {
    print(shape.area())
}

#[implements(shape, Shape2D)]
fn area_structural(shape) {
    print(shape.area())
}
```

## Declaration Decorators

Decorators wrap top-level sync functions with Python-like declaration syntax:

```zinc
fn logged(f: (i64) -> i64) -> (i64) -> i64 {
    return fn(x: i64) {
        print("logged")
        return f(x)
    }
}

@logged
fn inc(x: i64) -> i64 {
    return x + 1
}
```

`@decorator` means `decorator(target_function)`. `@decorator(args...)` means
`decorator(args...)(target_function)`, so factory arguments use ordinary Zinc
call binding, type checking, defaults, named arguments, and spread rules.

Stacked decorators apply bottom-up:

```zinc
@outer()
@inner
fn value(x: i64) -> i64 {
    return x
}
```

This wraps `value` as if `inner` receives the implementation first, then
`outer()` receives that wrapped callable.

Decorators are signature-preserving in v1. The callable returned by each
decorator must have the same parameter and return types as the decorated
function. Function annotations and `#[...]` constraints are checked before the
decorator chain is applied, and decorator functions or factories are checked
like ordinary calls.

Constraints must appear before decorators:

```zinc
#[x in [i64]]
@logged
fn checked(x) {
    return x
}
```

Decorators on structs, enums, methods, and async functions are parsed, but v1
reports a clear unsupported-feature error for those targets.

## Channels And Spawn

Channels are created with `chan()` or `chan(capacity)`:

```zinc
fn sender(ch, value) {
    ch <- value
}

fn main() {
    values = chan()

    spawn sender(values, 42)

    received = <- values
    print("{received}")
}
```

`chan()` creates an unbounded channel. `chan(n)` creates a bounded channel with
capacity `n`; sends on bounded channels may wait until capacity is available.

Use `<-` to send and receive:

```zinc
fn main() {
    ch = chan()

    ch <- 1
    value = <- ch

    print("{value}")
}
```

`select` chooses the first channel case that can proceed:

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

Receive bindings are local to the selected case block, so they can shadow outer
variables without changing them after the block exits. `default` is non-blocking:
it runs only when every other case would wait. Closed-channel receives and sends
still panic at runtime, matching Zinc's existing `unwrap()` behavior for channel
operations.

Use `spawn` to run a function concurrently:

```zinc
fn emit(x) {
    print("{x}")
}

fn main() {
    spawn emit(1)
    spawn emit(2)
    print("done")
}
```

Zinc promises that spawned tasks started by a function complete before that
function exits. At program exit, `main` waits for its spawned tasks. Spawned task
print order is still nondeterministic, so concurrent programs should not depend
on stdout ordering unless they synchronize through channels.

Nested spawns are also waited for by the function that starts them:

```zinc
fn child(x) {
    print("{x}")
}

fn parent(x) {
    spawn child(x + 1)
    print("{x}")
}

fn main() {
    spawn parent(10)
    print("done")
}
```

## Type Inference Rules To Know

Empty containers must have their element, key, or value types inferred before
the compiler validates the function:

```zinc
fn main() {
    values = []
    values.push(1) // now values is an integer array

    scores = dict()
    scores["a"] = 1 // now scores is dict<string, integer>
}
```

These are compile-time errors:

```zinc
fn main() {
    values = []
    // no push or other use establishes an element type

    scores = sort_dict()
    // no insert, index assignment, get, or contains_key establishes key/value types
}
```

Collection mutators are unit-valued expressions, so they can appear in value
position even though they do not produce a useful payload:

```zinc
fn main() {
    values = set()

    result = values.insert(1)
    print(values.len())
}
```

Tuple destructuring arity must match exactly:

```zinc
fn main() {
    a, b = (1, 2)

    // a, b, c = (1, 2) // error
}
```

## Current Limitations

- `{}` is not allowed because it is ambiguous.
- Empty arrays, sets, and dictionaries require type inference from later usage.
- Float dictionary keys and float set elements are rejected. (for now)
- Tuple indexing requires ..a literal integer index.
- Dictionary mutation during dictionary iteration is rejected.
- External package dependencies and re-export syntax are not implemented yet.

## Development Tests

The project test suite compiles Zinc fixtures to Rust goldens and runs the
generated binaries:

```sh
python -m pytest test/test_compile.py
```

Many language examples in this guide correspond directly to fixtures under
`test/zinc_source`.
