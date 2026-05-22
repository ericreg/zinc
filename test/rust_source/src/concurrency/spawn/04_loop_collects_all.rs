async fn concurrency_spawn_04_loop_collects_all__emit_UnboundedSender_i64(results: tokio::sync::mpsc::UnboundedSender<i64>, value: i64) {
    results.send(value).unwrap();
}

#[tokio::main]
async fn main() {
    let mut __zinc_spawn_handles = Vec::new();
    let (results_tx, mut results_rx) = tokio::sync::mpsc::unbounded_channel::<i64>();
    for i in 1..=4 {
        __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = results_tx.clone(); async move { concurrency_spawn_04_loop_collects_all__emit_UnboundedSender_i64(__zinc_spawn_arg_0, i).await; } }));
    }
    let mut total = 0;
    for i in 0..4 {
        let value = results_rx.recv().await.unwrap();
        total = (total + value);
    }
    println!("{}", total);
    while let Some(__zinc_spawn_handle) = __zinc_spawn_handles.pop() {
        __zinc_spawn_handle.await.unwrap();
    }
}