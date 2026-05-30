#[derive(Clone)]
struct __ZincClosureEnv_callables_10_return_lambda___lambda_callables_10_return_lambda__make_6_15 {
}

#[derive(Clone)]
enum __ZincCallable_i64_to_i64 {
    Closed,
    V0(__ZincClosureEnv_callables_10_return_lambda___lambda_callables_10_return_lambda__make_6_15),
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
            Self::V0(env) => callables_10_return_lambda____lambda_callables_10_return_lambda__make_6_15_i64(env.clone(), arg_0),
        }
    }
}

fn callables_10_return_lambda____lambda_callables_10_return_lambda__make_6_15_i64(__env: __ZincClosureEnv_callables_10_return_lambda___lambda_callables_10_return_lambda__make_6_15, x: i64) -> i64 {
    return (x + 1);
}

fn callables_10_return_lambda__make() -> __ZincCallable_i64_to_i64 {
    return __ZincCallable_i64_to_i64::V0(__ZincClosureEnv_callables_10_return_lambda___lambda_callables_10_return_lambda__make_6_15 {});
}

fn main() {
    let f = callables_10_return_lambda__make();
    println!("{}", f.call(4));
}