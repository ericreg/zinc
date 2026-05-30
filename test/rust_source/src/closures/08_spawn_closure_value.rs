use std::sync::{Arc, Mutex};

#[derive(Clone)]
struct __ZincClosureEnv_closures_08_spawn_closure_value___lambda_closures_08_spawn_closure_value__main_10_20 {
    base: Arc<Mutex<i64>>,
}

#[derive(Clone)]
enum __ZincCallable_Unit_to_Unit {
    Closed,
    V0(__ZincClosureEnv_closures_08_spawn_closure_value___lambda_closures_08_spawn_closure_value__main_10_20),
}

impl Default for __ZincCallable_Unit_to_Unit {
    fn default() -> Self {
        Self::Closed
    }
}

impl __ZincCallable_Unit_to_Unit {
    fn call(&self, ) {
        match self {
            Self::Closed => panic!("callable used after closed receive"),
            Self::V0(env) => { closures_08_spawn_closure_value____lambda_closures_08_spawn_closure_value__main_10_20(env.clone()); }
        }
    }
}

fn closures_08_spawn_closure_value____lambda_closures_08_spawn_closure_value__main_10_20(__env: __ZincClosureEnv_closures_08_spawn_closure_value___lambda_closures_08_spawn_closure_value__main_10_20) {
    let __zv_closures_08_spawn_closure_value____lambda_closures_08_spawn_closure_value__main_10_20_base_i64 = __env.base.clone();
    println!("{}", (*__zv_closures_08_spawn_closure_value____lambda_closures_08_spawn_closure_value__main_10_20_base_i64.lock().unwrap() + 1));
}

#[tokio::main]
async fn main() {
    let mut __zinc_spawn_handles = Vec::new();
    let __zv_closures_08_spawn_closure_value__main_base_i64 = Arc::new(Mutex::new(4));
    let worker = __ZincCallable_Unit_to_Unit::V0(__ZincClosureEnv_closures_08_spawn_closure_value___lambda_closures_08_spawn_closure_value__main_10_20 { base: __zv_closures_08_spawn_closure_value__main_base_i64.clone() });
    __zinc_spawn_handles.push(tokio::spawn(async move { worker.call(); }));
    while let Some(__zinc_spawn_handle) = __zinc_spawn_handles.pop() {
        __zinc_spawn_handle.await.unwrap();
    }
}