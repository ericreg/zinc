#[derive(Clone)]
struct __ZincClosureEnv_callables_02_lambda_array___lambda_callables_02_lambda_array__main_13_22 {
}

#[derive(Clone)]
enum __ZincCallable_i64_to_i64 {
    Closed,
    V0(__ZincClosureEnv_callables_02_lambda_array___lambda_callables_02_lambda_array__main_13_22),
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
            Self::V0(env) => callables_02_lambda_array____lambda_callables_02_lambda_array__main_13_22_i64(env.clone(), arg_0),
        }
    }
}

fn callables_02_lambda_array____lambda_callables_02_lambda_array__main_13_22_i64(__env: __ZincClosureEnv_callables_02_lambda_array___lambda_callables_02_lambda_array__main_13_22, x: i64) -> i64 {
    return (x + 1);
}

fn main() {
    let mut ops = vec![];
    ops.push(__ZincCallable_i64_to_i64::V0(__ZincClosureEnv_callables_02_lambda_array___lambda_callables_02_lambda_array__main_13_22 {}));
    println!("{}", ops[0].call(10));
}