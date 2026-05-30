use zinc_internal::{__ZincChannel};

#[derive(Clone)]
struct __ZincClosureEnv_callables_16_channel_lambda___lambda_callables_16_channel_lambda__main_12_23 {
}

#[derive(Clone)]
enum __ZincCallable_i64_to_i64 {
    Closed,
    V0(__ZincClosureEnv_callables_16_channel_lambda___lambda_callables_16_channel_lambda__main_12_23),
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
            Self::V0(env) => callables_16_channel_lambda____lambda_callables_16_channel_lambda__main_12_23_i64(env.clone(), arg_0),
        }
    }
}

fn callables_16_channel_lambda____lambda_callables_16_channel_lambda__main_12_23_i64(__env: __ZincClosureEnv_callables_16_channel_lambda___lambda_callables_16_channel_lambda__main_12_23, x: i64) -> i64 {
    return (x + 2);
}

#[tokio::main]
async fn main() {
    let jobs = __ZincChannel::<__ZincCallable_i64_to_i64>::unbounded();
    jobs.send(__ZincCallable_i64_to_i64::V0(__ZincClosureEnv_callables_16_channel_lambda___lambda_callables_16_channel_lambda__main_12_23 {})).await;
    let f = jobs.recv().await;
    println!("{}", f.call(3));
}