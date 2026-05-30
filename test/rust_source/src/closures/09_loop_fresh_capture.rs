use std::sync::{Arc, Mutex};

#[derive(Clone)]
struct __ZincClosureEnv_closures_09_loop_fresh_capture___lambda_closures_09_loop_fresh_capture__main_20_26 {
    i: Arc<Mutex<i64>>,
}

#[derive(Clone)]
enum __ZincCallable_Unit_to_i64 {
    Closed,
    V0(__ZincClosureEnv_closures_09_loop_fresh_capture___lambda_closures_09_loop_fresh_capture__main_20_26),
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
            Self::V0(env) => closures_09_loop_fresh_capture____lambda_closures_09_loop_fresh_capture__main_20_26(env.clone()),
        }
    }
}

fn closures_09_loop_fresh_capture____lambda_closures_09_loop_fresh_capture__main_20_26(__env: __ZincClosureEnv_closures_09_loop_fresh_capture___lambda_closures_09_loop_fresh_capture__main_20_26) -> i64 {
    let __zv_closures_09_loop_fresh_capture____lambda_closures_09_loop_fresh_capture__main_20_26_i_i64 = __env.i.clone();
    return *__zv_closures_09_loop_fresh_capture____lambda_closures_09_loop_fresh_capture__main_20_26_i_i64.lock().unwrap();
}

fn main() {
    let mut funcs = vec![];
    for __zinc_for_value_0 in 0..3 {
        let __zv_closures_09_loop_fresh_capture__main_for_0_i_i64 = Arc::new(Mutex::new(__zinc_for_value_0));
        funcs.push(__ZincCallable_Unit_to_i64::V0(__ZincClosureEnv_closures_09_loop_fresh_capture___lambda_closures_09_loop_fresh_capture__main_20_26 { i: __zv_closures_09_loop_fresh_capture__main_for_0_i_i64.clone() }));
    }
    println!("{}", funcs[0].call());
    println!("{}", funcs[1].call());
    println!("{}", funcs[2].call());
}