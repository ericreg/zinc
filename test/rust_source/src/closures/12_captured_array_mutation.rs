use std::sync::{Arc, Mutex};

#[derive(Clone)]
struct __ZincClosureEnv_closures_12_captured_array_mutation___lambda_closures_12_captured_array_mutation__main_12_23 {
    items: Arc<Mutex<Vec<i64>>>,
}

#[derive(Clone)]
enum __ZincCallable_i64_to_Unit {
    Closed,
    V0(__ZincClosureEnv_closures_12_captured_array_mutation___lambda_closures_12_captured_array_mutation__main_12_23),
}

impl Default for __ZincCallable_i64_to_Unit {
    fn default() -> Self {
        Self::Closed
    }
}

impl __ZincCallable_i64_to_Unit {
    fn call(&self, arg_0: i64) {
        match self {
            Self::Closed => panic!("callable used after closed receive"),
            Self::V0(env) => { closures_12_captured_array_mutation____lambda_closures_12_captured_array_mutation__main_12_23_i64(env.clone(), arg_0); }
        }
    }
}

fn closures_12_captured_array_mutation____lambda_closures_12_captured_array_mutation__main_12_23_i64(__env: __ZincClosureEnv_closures_12_captured_array_mutation___lambda_closures_12_captured_array_mutation__main_12_23, x: i64) {
    let __zv_closures_12_captured_array_mutation____lambda_closures_12_captured_array_mutation__main_12_23_i64_items_Vec = __env.items.clone();
    __zv_closures_12_captured_array_mutation____lambda_closures_12_captured_array_mutation__main_12_23_i64_items_Vec.lock().unwrap().push(x);
}

fn main() {
    let __zv_closures_12_captured_array_mutation__main_items_Vec = Arc::new(Mutex::new(vec![1]));
    let push_item = __ZincCallable_i64_to_Unit::V0(__ZincClosureEnv_closures_12_captured_array_mutation___lambda_closures_12_captured_array_mutation__main_12_23 { items: __zv_closures_12_captured_array_mutation__main_items_Vec.clone() });
    push_item.call(3);
    push_item.call(4);
    println!("{}", __zv_closures_12_captured_array_mutation__main_items_Vec.lock().unwrap()[1]);
    println!("{}", __zv_closures_12_captured_array_mutation__main_items_Vec.lock().unwrap()[2]);
}