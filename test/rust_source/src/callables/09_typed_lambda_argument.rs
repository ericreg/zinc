#[derive(Clone)]
enum __ZincCallable_i64_to_i64 {
    V0,
}

impl __ZincCallable_i64_to_i64 {
    fn call(&self, arg_0: i64) -> i64 {
        match self {
            Self::V0 => callables_09_typed_lambda_argument____lambda_31_42_i64(arg_0),
        }
    }
}

fn callables_09_typed_lambda_argument____lambda_31_42_i64(value: i64) -> i64 {
    return (value * 3);
}

fn callables_09_typed_lambda_argument__apply_i64_to_unknown_i64(f: __ZincCallable_i64_to_i64, x: i64) -> i64 {
    return f.call(x);
}

fn main() {
    println!("{}", callables_09_typed_lambda_argument__apply_i64_to_unknown_i64(__ZincCallable_i64_to_i64::V0, 4));
}