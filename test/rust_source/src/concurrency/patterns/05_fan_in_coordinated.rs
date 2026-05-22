async fn concurrency_patterns_05_fan_in_coordinated__send_left_UnboundedSender(out: tokio::sync::mpsc::UnboundedSender<i64>) {
    out.send(1).unwrap();
}

async fn concurrency_patterns_05_fan_in_coordinated__send_right_UnboundedSender(out: tokio::sync::mpsc::UnboundedSender<i64>) {
    out.send(2).unwrap();
}

#[tokio::main]
async fn main() {
    let mut __zinc_spawn_handles = Vec::new();
    let (left_tx, mut left_rx) = tokio::sync::mpsc::unbounded_channel::<i64>();
    let (right_tx, mut right_rx) = tokio::sync::mpsc::unbounded_channel::<i64>();
    let (merged_tx, mut merged_rx) = tokio::sync::mpsc::unbounded_channel::<i64>();
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = left_tx.clone(); async move { concurrency_patterns_05_fan_in_coordinated__send_left_UnboundedSender(__zinc_spawn_arg_0).await; } }));
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = right_tx.clone(); async move { concurrency_patterns_05_fan_in_coordinated__send_right_UnboundedSender(__zinc_spawn_arg_0).await; } }));
    let left_value = left_rx.recv().await.unwrap();
    let right_value = right_rx.recv().await.unwrap();
    merged_tx.send(left_value).unwrap();
    merged_tx.send(right_value).unwrap();
    println!("{}", merged_rx.recv().await.unwrap());
    println!("{}", merged_rx.recv().await.unwrap());
    while let Some(__zinc_spawn_handle) = __zinc_spawn_handles.pop() {
        __zinc_spawn_handle.await.unwrap();
    }
}