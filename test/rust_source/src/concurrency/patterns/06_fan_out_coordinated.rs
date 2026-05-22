async fn concurrency_patterns_06_fan_out_coordinated__double_UnboundedSender_i64(out: tokio::sync::mpsc::UnboundedSender<i64>, value: i64) {
    out.send((value * 2)).unwrap();
}

async fn concurrency_patterns_06_fan_out_coordinated__triple_UnboundedSender_i64(out: tokio::sync::mpsc::UnboundedSender<i64>, value: i64) {
    out.send((value * 3)).unwrap();
}

#[tokio::main]
async fn main() {
    let mut __zinc_spawn_handles = Vec::new();
    let (doubles_tx, mut doubles_rx) = tokio::sync::mpsc::unbounded_channel::<i64>();
    let (triples_tx, mut triples_rx) = tokio::sync::mpsc::unbounded_channel::<i64>();
    let source = 5;
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = doubles_tx.clone(); async move { concurrency_patterns_06_fan_out_coordinated__double_UnboundedSender_i64(__zinc_spawn_arg_0, source).await; } }));
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = triples_tx.clone(); async move { concurrency_patterns_06_fan_out_coordinated__triple_UnboundedSender_i64(__zinc_spawn_arg_0, source).await; } }));
    println!("{}", doubles_rx.recv().await.unwrap());
    println!("{}", triples_rx.recv().await.unwrap());
    while let Some(__zinc_spawn_handle) = __zinc_spawn_handles.pop() {
        __zinc_spawn_handle.await.unwrap();
    }
}