use std::sync::{Arc, Mutex};

#[derive(Clone)]
struct __ZincClosureEnv_closures_06_generic_apply_capture___lambda_closures_06_generic_apply_capture__main_26_37 {
    offset: Arc<Mutex<i64>>,
}

#[derive(Clone)]
enum __ZincCallable_i64_to_i64 {
    Closed,
    V0(__ZincClosureEnv_closures_06_generic_apply_capture___lambda_closures_06_generic_apply_capture__main_26_37),
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
            Self::V0(env) => closures_06_generic_apply_capture____lambda_closures_06_generic_apply_capture__main_26_37_i64(env.clone(), arg_0),
        }
    }
}

fn closures_06_generic_apply_capture____lambda_closures_06_generic_apply_capture__main_26_37_i64(__env: __ZincClosureEnv_closures_06_generic_apply_capture___lambda_closures_06_generic_apply_capture__main_26_37, x: i64) -> i64 {
    let __zv_closures_06_generic_apply_capture____lambda_closures_06_generic_apply_capture__main_26_37_i64_offset_i64 = __env.offset.clone();
    return (*__zv_closures_06_generic_apply_capture____lambda_closures_06_generic_apply_capture__main_26_37_i64_offset_i64.lock().unwrap() + x);
}

fn closures_06_generic_apply_capture__apply_i64_to_unknown_i64(f: __ZincCallable_i64_to_i64, x: i64) -> i64 {
    return f.call(x);
}

fn main() {
    let __zv_closures_06_generic_apply_capture__main_offset_i64 = Arc::new(Mutex::new(5));
    println!("{}", closures_06_generic_apply_capture__apply_i64_to_unknown_i64(__ZincCallable_i64_to_i64::V0(__ZincClosureEnv_closures_06_generic_apply_capture___lambda_closures_06_generic_apply_capture__main_26_37 { offset: __zv_closures_06_generic_apply_capture__main_offset_i64.clone() }), 7));
}