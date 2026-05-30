use zinc_internal::{Channel};
use std::sync::{Arc, Mutex};

#[derive(Clone)]
struct __ZincClosureEnv_closures_07_channel_send_closure___lambda_closures_07_channel_send_closure__main_15_24 {
    base: Arc<Mutex<i64>>,
}

#[derive(Clone)]
enum __ZincCallable_i64_to_i64 {
    Closed,
    V0(__ZincClosureEnv_closures_07_channel_send_closure___lambda_closures_07_channel_send_closure__main_15_24),
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
            Self::V0(env) => closures_07_channel_send_closure____lambda_closures_07_channel_send_closure__main_15_24_i64(env.clone(), arg_0),
        }
    }
}

fn closures_07_channel_send_closure____lambda_closures_07_channel_send_closure__main_15_24_i64(__env: __ZincClosureEnv_closures_07_channel_send_closure___lambda_closures_07_channel_send_closure__main_15_24, x: i64) -> i64 {
    let __zv_closures_07_channel_send_closure____lambda_closures_07_channel_send_closure__main_15_24_i64_base_i64 = __env.base.clone();
    return (*__zv_closures_07_channel_send_closure____lambda_closures_07_channel_send_closure__main_15_24_i64_base_i64.lock().unwrap() + x);
}

#[tokio::main]
async fn main() {
    let __zv_closures_07_channel_send_closure__main_base_i64 = Arc::new(Mutex::new(4));
    let jobs = Channel::<__ZincCallable_i64_to_i64>::unbounded();
    jobs.send(__ZincCallable_i64_to_i64::V0(__ZincClosureEnv_closures_07_channel_send_closure___lambda_closures_07_channel_send_closure__main_15_24 { base: __zv_closures_07_channel_send_closure__main_base_i64.clone() })).await;
    jobs.close();
    let job = jobs.recv().await;
    println!("{}", job.call(3));
}