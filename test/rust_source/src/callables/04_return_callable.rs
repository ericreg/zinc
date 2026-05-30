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
            Self::V0 => callables_04_return_callable__inc_i64(arg_0),
        }
    }
}

fn callables_04_return_callable__inc_i64(x: i64) -> i64 {
    return (x + 1);
}

fn callables_04_return_callable__make() -> __ZincCallable_i64_to_i64 {
    return __ZincCallable_i64_to_i64::V0;
}

fn main() {
    let f = callables_04_return_callable__make();
    println!("{}", f.call(3));
}