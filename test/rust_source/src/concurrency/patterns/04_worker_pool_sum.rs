use zinc_internal::{Channel};

async fn concurrency_patterns_04_worker_pool_sum__worker_Channel_i64(results: Channel<i64>, value: i64) {
    results.send((value * value)).await;
}

#[tokio::main]
async fn main() {
    let mut __zinc_spawn_handles = Vec::new();
    let results = Channel::<i64>::unbounded();
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = results.clone(); async move { concurrency_patterns_04_worker_pool_sum__worker_Channel_i64(__zinc_spawn_arg_0.clone(), 1).await; } }));
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = results.clone(); async move { concurrency_patterns_04_worker_pool_sum__worker_Channel_i64(__zinc_spawn_arg_0.clone(), 2).await; } }));
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = results.clone(); async move { concurrency_patterns_04_worker_pool_sum__worker_Channel_i64(__zinc_spawn_arg_0.clone(), 3).await; } }));
    let mut total = 0;
    for i in 0..3 {
        let value = results.recv().await;
        total = (total + value);
    }
    println!("{}", total);
    while let Some(__zinc_spawn_handle) = __zinc_spawn_handles.pop() {
        __zinc_spawn_handle.await.unwrap();
    }
}