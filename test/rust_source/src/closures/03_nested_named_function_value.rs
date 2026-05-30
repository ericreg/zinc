use std::sync::{Arc, Mutex};

#[derive(Clone)]
struct __ZincClosureEnv_closures_03_nested_named_function_value___lexical_closures_03_nested_named_function_value__main_add_8_18 {
    x: Arc<Mutex<i64>>,
}

#[derive(Clone)]
enum __ZincCallable_i64_to_i64 {
    Closed,
    V0(__ZincClosureEnv_closures_03_nested_named_function_value___lexical_closures_03_nested_named_function_value__main_add_8_18),
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
            Self::V0(env) => closures_03_nested_named_function_value____lexical_closures_03_nested_named_function_value__main_add_8_18_i64(env.clone(), arg_0),
        }
    }
}

fn closures_03_nested_named_function_value____lexical_closures_03_nested_named_function_value__main_add_8_18_i64(__env: __ZincClosureEnv_closures_03_nested_named_function_value___lexical_closures_03_nested_named_function_value__main_add_8_18, y: i64) -> i64 {
    let __zv_closures_03_nested_named_function_value____lexical_closures_03_nested_named_function_value__main_add_8_18_i64_x_i64 = __env.x.clone();
    return (*__zv_closures_03_nested_named_function_value____lexical_closures_03_nested_named_function_value__main_add_8_18_i64_x_i64.lock().unwrap() + y);
}

fn main() {
    let __zv_closures_03_nested_named_function_value__main_x_i64 = Arc::new(Mutex::new(2));
    println!("{}", closures_03_nested_named_function_value____lexical_closures_03_nested_named_function_value__main_add_8_18_i64(__ZincClosureEnv_closures_03_nested_named_function_value___lexical_closures_03_nested_named_function_value__main_add_8_18 { x: __zv_closures_03_nested_named_function_value__main_x_i64.clone() }, 3));
    let f = __ZincCallable_i64_to_i64::V0(__ZincClosureEnv_closures_03_nested_named_function_value___lexical_closures_03_nested_named_function_value__main_add_8_18 { x: __zv_closures_03_nested_named_function_value__main_x_i64.clone() });
    println!("{}", f.call(4));
}