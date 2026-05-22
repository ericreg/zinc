async fn concurrency_patterns_04_worker_pool_sum__worker_UnboundedSender_i64(results: tokio::sync::mpsc::UnboundedSender<i64>, value: i64) {
    results.send((value * value)).unwrap();
}

#[tokio::main]
async fn main() {
    let mut __zinc_spawn_handles = Vec::new();
    let (results_tx, mut results_rx) = tokio::sync::mpsc::unbounded_channel::<i64>();
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = results_tx.clone(); async move { concurrency_patterns_04_worker_pool_sum__worker_UnboundedSender_i64(__zinc_spawn_arg_0, 1).await; } }));
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = results_tx.clone(); async move { concurrency_patterns_04_worker_pool_sum__worker_UnboundedSender_i64(__zinc_spawn_arg_0, 2).await; } }));
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = results_tx.clone(); async move { concurrency_patterns_04_worker_pool_sum__worker_UnboundedSender_i64(__zinc_spawn_arg_0, 3).await; } }));
    let mut total = 0;
    for i in 0..3 {
        let value = results_rx.recv().await.unwrap();
        total = (total + value);
    }
    println!("{}", total);
    while let Some(__zinc_spawn_handle) = __zinc_spawn_handles.pop() {
        __zinc_spawn_handle.await.unwrap();
    }
}