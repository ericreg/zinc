use std::sync::{Arc, Mutex};

#[derive(Clone)]
struct __ZincClosureEnv_closures_11_nested_async_capture___lexical_closures_11_nested_async_capture__main_inner_8_20 {
    base: Arc<Mutex<i64>>,
}

async fn closures_11_nested_async_capture____lexical_closures_11_nested_async_capture__main_inner_8_20_i64(__env: __ZincClosureEnv_closures_11_nested_async_capture___lexical_closures_11_nested_async_capture__main_inner_8_20, x: i64) {
    let __zv_closures_11_nested_async_capture____lexical_closures_11_nested_async_capture__main_inner_8_20_i64_base_i64 = __env.base.clone();
    println!("{}", (*__zv_closures_11_nested_async_capture____lexical_closures_11_nested_async_capture__main_inner_8_20_i64_base_i64.lock().unwrap() + x));
}

#[tokio::main]
async fn main() {
    let __zv_closures_11_nested_async_capture__main_base_i64 = Arc::new(Mutex::new(2));
    closures_11_nested_async_capture____lexical_closures_11_nested_async_capture__main_inner_8_20_i64(__ZincClosureEnv_closures_11_nested_async_capture___lexical_closures_11_nested_async_capture__main_inner_8_20 { base: __zv_closures_11_nested_async_capture__main_base_i64.clone() }, 3).await;
}