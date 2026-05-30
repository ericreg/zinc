#[derive(Clone)]
enum __ZincCallable_i64_to_i64 {
    Closed,
    V0,
}

impl Default for __ZincCallable_i64_to_i64 {
    fn default() -> Self {
        Self::Closed
    }
}

impl __ZincCallable_i64_to_i64 {
    fn call(&self, arg_0: i64) -> i64 {
        match self {
            Self::Closed => panic!("callable used after closed receive"),
            Self::V0 => callables_05_static_method__Math::add_one(arg_0),
        }
    }
}

struct callables_05_static_method__Math {
}

impl Default for callables_05_static_method__Math {
    fn default() -> Self {
        Self {  }
    }
}

impl callables_05_static_method__Math {
    fn add_one(x: i64) -> i64 {
        return (x + 1);
    }
}

fn main() {
    let f = __ZincCallable_i64_to_i64::V0;
    println!("{}", f.call(4));
}