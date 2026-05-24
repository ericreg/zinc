#[derive(Clone)]
enum __ZincCallable_i64_to_i64 {
    V0,
}

impl __ZincCallable_i64_to_i64 {
    fn call(&self, arg_0: i64) -> i64 {
        match self {
            Self::V0 => callables_05_static_method__Math::add_one(arg_0),
        }
    }
}

struct callables_05_static_method__Math {
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