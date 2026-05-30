use std::sync::{Arc, Mutex};

#[derive(Clone)]
struct __ZincClosureEnv_closures_01_lambda_capture_read___lambda_closures_01_lambda_capture_read__main_10_18 {
    x: Arc<Mutex<i64>>,
}

#[derive(Clone)]
enum __ZincCallable_Unit_to_i64 {
    Closed,
    V0(__ZincClosureEnv_closures_01_lambda_capture_read___lambda_closures_01_lambda_capture_read__main_10_18),
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
            Self::V0(env) => closures_01_lambda_capture_read____lambda_closures_01_lambda_capture_read__main_10_18(env.clone()),
        }
    }
}

fn closures_01_lambda_capture_read____lambda_closures_01_lambda_capture_read__main_10_18(__env: __ZincClosureEnv_closures_01_lambda_capture_read___lambda_closures_01_lambda_capture_read__main_10_18) -> i64 {
    let __zv_closures_01_lambda_capture_read____lambda_closures_01_lambda_capture_read__main_10_18_x_i64 = __env.x.clone();
    return (*__zv_closures_01_lambda_capture_read____lambda_closures_01_lambda_capture_read__main_10_18_x_i64.lock().unwrap() + 1);
}

fn main() {
    let __zv_closures_01_lambda_capture_read__main_x_i64 = Arc::new(Mutex::new(3));
    let f = __ZincCallable_Unit_to_i64::V0(__ZincClosureEnv_closures_01_lambda_capture_read___lambda_closures_01_lambda_capture_read__main_10_18 { x: __zv_closures_01_lambda_capture_read__main_x_i64.clone() });
    println!("{}", f.call());
}