#[derive(Clone)]
enum __ZincCallable_i64_to_i64 {
    V0,
}

impl __ZincCallable_i64_to_i64 {
    fn call(&self, arg_0: i64) -> i64 {
        match self {
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
    let f = __ZincCallable_i64_to_i64::V0;
    println!("{}", f.call(3));
}