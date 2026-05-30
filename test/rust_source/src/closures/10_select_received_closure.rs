use zinc_internal::{__ZincChannel};
use std::sync::{Arc, Mutex};

#[derive(Clone)]
struct __ZincClosureEnv_closures_10_select_received_closure___lambda_closures_10_select_received_closure__main_15_24 {
    base: Arc<Mutex<i64>>,
}

#[derive(Clone)]
enum __ZincCallable_i64_to_i64 {
    Closed,
    V0(__ZincClosureEnv_closures_10_select_received_closure___lambda_closures_10_select_received_closure__main_15_24),
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
            Self::V0(env) => closures_10_select_received_closure____lambda_closures_10_select_received_closure__main_15_24_i64(env.clone(), arg_0),
        }
    }
}

fn closures_10_select_received_closure____lambda_closures_10_select_received_closure__main_15_24_i64(__env: __ZincClosureEnv_closures_10_select_received_closure___lambda_closures_10_select_received_closure__main_15_24, x: i64) -> i64 {
    let __zv_closures_10_select_received_closure____lambda_closures_10_select_received_closure__main_15_24_i64_base_i64 = __env.base.clone();
    return (*__zv_closures_10_select_received_closure____lambda_closures_10_select_received_closure__main_15_24_i64_base_i64.lock().unwrap() + x);
}

#[tokio::main]
async fn main() {
    let __zv_closures_10_select_received_closure__main_base_i64 = Arc::new(Mutex::new(8));
    let jobs = __ZincChannel::<__ZincCallable_i64_to_i64>::unbounded();
    jobs.send(__ZincCallable_i64_to_i64::V0(__ZincClosureEnv_closures_10_select_received_closure___lambda_closures_10_select_received_closure__main_15_24 { base: __zv_closures_10_select_received_closure__main_base_i64.clone() })).await;
    jobs.close();
    tokio::select! {
        __zinc_select_value_0_0 = async { jobs.recv_option().await } => {
            let job = match __zinc_select_value_0_0 { Some(value) => value, None => panic!("select receive on closed channel") };
            println!("{}", job.call(2));
        },
    }
}