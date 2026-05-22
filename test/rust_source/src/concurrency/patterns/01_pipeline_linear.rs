async fn concurrency_patterns_01_pipeline_linear__source_UnboundedSender(out: tokio::sync::mpsc::UnboundedSender<i64>) {
    out.send(5).unwrap();
}

#[tokio::main]
async fn main() {
    let mut __zinc_spawn_handles = Vec::new();
    let (stage1_tx, mut stage1_rx) = tokio::sync::mpsc::unbounded_channel::<i64>();
    let (stage2_tx, mut stage2_rx) = tokio::sync::mpsc::unbounded_channel::<i64>();
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = stage1_tx.clone(); async move { concurrency_patterns_01_pipeline_linear__source_UnboundedSender(__zinc_spawn_arg_0).await; } }));
    let value = stage1_rx.recv().await.unwrap();
    stage2_tx.send((value * 2)).unwrap();
    let result = stage2_rx.recv().await.unwrap();
    println!("{}", result);
    while let Some(__zinc_spawn_handle) = __zinc_spawn_handles.pop() {
        __zinc_spawn_handle.await.unwrap();
    }
}