#[derive(Clone)]
enum __ZincCallable_i64_i64_to_i64 {
    Closed,
    V0,
}

impl Default for __ZincCallable_i64_i64_to_i64 {
    fn default() -> Self {
        Self::Closed
    }
}

impl __ZincCallable_i64_i64_to_i64 {
    fn call(&self, arg_0: i64, arg_1: i64) -> i64 {
        match self {
            Self::Closed => panic!("callable used after closed receive"),
            Self::V0 => modules__lib_math__add_i64_i64(arg_0, arg_1),
        }
    }
}

fn modules__lib_math__add_i64_i64(a: i64, b: i64) -> i64 {
    return (a + b);
}

fn main() {
    let f = __ZincCallable_i64_i64_to_i64::V0;
    println!("{}", f.call(2, 3));
}