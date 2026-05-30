use zinc_internal::{__ZincChannel};

#[derive(Clone)]
enum __ZincCallable_i64_to_i64 {
    Closed,
    V0,
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
            Self::V0 => callables_18_channel_spawn_helper__inc_i64(arg_0),
        }
    }
}

fn callables_18_channel_spawn_helper__inc_i64(x: i64) -> i64 {
    return (x + 1);
}

async fn callables_18_channel_spawn_helper__worker_Channel(out: __ZincChannel<__ZincCallable_i64_to_i64>) {
    out.send(__ZincCallable_i64_to_i64::V0).await;
}

async fn callables_18_channel_spawn_helper__worker_Channel_i64_to_i64(out: __ZincChannel<__ZincCallable_i64_to_i64>) {
    out.send(__ZincCallable_i64_to_i64::V0).await;
}

async fn callables_18_channel_spawn_helper__worker_Channel_i64_to_unknown(out: __ZincChannel<__ZincCallable_i64_to_i64>) {
    out.send(__ZincCallable_i64_to_i64::V0).await;
}

async fn callables_18_channel_spawn_helper__worker_Channel_unknown_to_unknown(out: __ZincChannel<__ZincCallable_i64_to_i64>) {
    out.send(__ZincCallable_i64_to_i64::V0).await;
}

#[tokio::main]
async fn main() {
    let mut __zinc_spawn_handles = Vec::new();
    let jobs = __ZincChannel::<__ZincCallable_i64_to_i64>::unbounded();
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = jobs.clone(); async move { callables_18_channel_spawn_helper__worker_Channel_i64_to_i64(__zinc_spawn_arg_0.clone()).await; } }));
    let f = jobs.recv().await;
    println!("{}", f.call(5));
    while let Some(__zinc_spawn_handle) = __zinc_spawn_handles.pop() {
        __zinc_spawn_handle.await.unwrap();
    }
}