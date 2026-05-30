use std::sync::{Arc, Mutex};

#[derive(Clone)]
struct __ZincClosureEnv_closures_02_lambda_super_assign___lambda_closures_02_lambda_super_assign__make_counter_i64_10_22 {
    x: Arc<Mutex<i64>>,
}

#[derive(Clone)]
enum __ZincCallable_Unit_to_i64 {
    Closed,
    V0(__ZincClosureEnv_closures_02_lambda_super_assign___lambda_closures_02_lambda_super_assign__make_counter_i64_10_22),
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
            Self::V0(env) => closures_02_lambda_super_assign____lambda_closures_02_lambda_super_assign__make_counter_i64_10_22(env.clone()),
        }
    }
}

fn closures_02_lambda_super_assign____lambda_closures_02_lambda_super_assign__make_counter_i64_10_22(__env: __ZincClosureEnv_closures_02_lambda_super_assign___lambda_closures_02_lambda_super_assign__make_counter_i64_10_22) -> i64 {
    let __zv_closures_02_lambda_super_assign____lambda_closures_02_lambda_super_assign__make_counter_i64_10_22_x_i64 = __env.x.clone();
    let __zinc_captured_write_14_19 = (*__zv_closures_02_lambda_super_assign____lambda_closures_02_lambda_super_assign__make_counter_i64_10_22_x_i64.lock().unwrap() + 1);
    *__zv_closures_02_lambda_super_assign____lambda_closures_02_lambda_super_assign__make_counter_i64_10_22_x_i64.lock().unwrap() = __zinc_captured_write_14_19;
    return *__zv_closures_02_lambda_super_assign____lambda_closures_02_lambda_super_assign__make_counter_i64_10_22_x_i64.lock().unwrap();
}

fn closures_02_lambda_super_assign__make_counter_i64(start: i64) -> __ZincCallable_Unit_to_i64 {
    let __zv_closures_02_lambda_super_assign__make_counter_i64_x_i64 = Arc::new(Mutex::new(start));
    return __ZincCallable_Unit_to_i64::V0(__ZincClosureEnv_closures_02_lambda_super_assign___lambda_closures_02_lambda_super_assign__make_counter_i64_10_22 { x: __zv_closures_02_lambda_super_assign__make_counter_i64_x_i64.clone() });
}

fn main() {
    let counter = closures_02_lambda_super_assign__make_counter_i64(0);
    println!("{}", counter.call());
    println!("{}", counter.call());
}