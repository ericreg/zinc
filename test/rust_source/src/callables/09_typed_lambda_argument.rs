#[derive(Clone)]
struct __ZincClosureEnv_callables_09_typed_lambda_argument___lambda_callables_09_typed_lambda_argument__main_31_42 {
}

#[derive(Clone)]
enum __ZincCallable_i64_to_i64 {
    Closed,
    V0(__ZincClosureEnv_callables_09_typed_lambda_argument___lambda_callables_09_typed_lambda_argument__main_31_42),
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
            Self::V0(env) => callables_09_typed_lambda_argument____lambda_callables_09_typed_lambda_argument__main_31_42_i64(env.clone(), arg_0),
        }
    }
}

fn callables_09_typed_lambda_argument____lambda_callables_09_typed_lambda_argument__main_31_42_i64(__env: __ZincClosureEnv_callables_09_typed_lambda_argument___lambda_callables_09_typed_lambda_argument__main_31_42, value: i64) -> i64 {
    return (value * 3);
}

fn callables_09_typed_lambda_argument__apply_i64_to_unknown_i64(f: __ZincCallable_i64_to_i64, x: i64) -> i64 {
    return f.call(x);
}

fn main() {
    println!("{}", callables_09_typed_lambda_argument__apply_i64_to_unknown_i64(__ZincCallable_i64_to_i64::V0(__ZincClosureEnv_callables_09_typed_lambda_argument___lambda_callables_09_typed_lambda_argument__main_31_42 {}), 4));
}