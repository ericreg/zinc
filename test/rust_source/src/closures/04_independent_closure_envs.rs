use std::sync::{Arc, Mutex};

#[derive(Clone)]
struct __ZincClosureEnv_closures_04_independent_closure_envs___lambda_closures_04_independent_closure_envs__make_counter_i64_10_20 {
    x: Arc<Mutex<i64>>,
}

#[derive(Clone)]
enum __ZincCallable_Unit_to_i64 {
    Closed,
    V0(__ZincClosureEnv_closures_04_independent_closure_envs___lambda_closures_04_independent_closure_envs__make_counter_i64_10_20),
}

impl Default for __ZincCallable_Unit_to_i64 {
    fn default() -> Self {
        Self::Closed
    }
}

impl __ZincCallable_Unit_to_i64 {
    fn call(&self, ) -> i64 {
        match self {
            Self::Closed => panic!("callable used after closed receive"),
            Self::V0(env) => closures_04_independent_closure_envs____lambda_closures_04_independent_closure_envs__make_counter_i64_10_20(env.clone()),
        }
    }
}

fn closures_04_independent_closure_envs____lambda_closures_04_independent_closure_envs__make_counter_i64_10_20(__env: __ZincClosureEnv_closures_04_independent_closure_envs___lambda_closures_04_independent_closure_envs__make_counter_i64_10_20) -> i64 {
    let __zv_closures_04_independent_closure_envs____lambda_closures_04_independent_closure_envs__make_counter_i64_10_20_x_i64 = __env.x.clone();
    let __zinc_captured_compound_17_17 = 1;
    *__zv_closures_04_independent_closure_envs____lambda_closures_04_independent_closure_envs__make_counter_i64_10_20_x_i64.lock().unwrap() += __zinc_captured_compound_17_17;
    return *__zv_closures_04_independent_closure_envs____lambda_closures_04_independent_closure_envs__make_counter_i64_10_20_x_i64.lock().unwrap();
}

fn closures_04_independent_closure_envs__make_counter_i64(start: i64) -> __ZincCallable_Unit_to_i64 {
    let __zv_closures_04_independent_closure_envs__make_counter_i64_x_i64 = Arc::new(Mutex::new(start));
    return __ZincCallable_Unit_to_i64::V0(__ZincClosureEnv_closures_04_independent_closure_envs___lambda_closures_04_independent_closure_envs__make_counter_i64_10_20 { x: __zv_closures_04_independent_closure_envs__make_counter_i64_x_i64.clone() });
}

fn main() {
    let first = closures_04_independent_closure_envs__make_counter_i64(0);
    let second = closures_04_independent_closure_envs__make_counter_i64(10);
    println!("{}", first.call());
    println!("{}", first.call());
    println!("{}", second.call());
}