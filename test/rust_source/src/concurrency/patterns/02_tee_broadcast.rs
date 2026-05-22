async fn concurrency_patterns_02_tee_broadcast__source_UnboundedSender(out: tokio::sync::mpsc::UnboundedSender<i64>) {
    out.send(3).unwrap();
}

#[tokio::main]
async fn main() {
    let mut __zinc_spawn_handles = Vec::new();
    let (input_tx, mut input_rx) = tokio::sync::mpsc::unbounded_channel::<i64>();
    let (left_tx, mut left_rx) = tokio::sync::mpsc::unbounded_channel::<i64>();
    let (right_tx, mut right_rx) = tokio::sync::mpsc::unbounded_channel::<i64>();
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = input_tx.clone(); async move { concurrency_patterns_02_tee_broadcast__source_UnboundedSender(__zinc_spawn_arg_0).await; } }));
    let value = input_rx.recv().await.unwrap();
    left_tx.send(value).unwrap();
    right_tx.send(value).unwrap();
    println!("{}", left_rx.recv().await.unwrap());
    println!("{}", right_rx.recv().await.unwrap());
    while let Some(__zinc_spawn_handle) = __zinc_spawn_handles.pop() {
        __zinc_spawn_handle.await.unwrap();
    }
}