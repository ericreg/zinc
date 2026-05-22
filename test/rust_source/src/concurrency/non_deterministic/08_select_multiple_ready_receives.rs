async fn concurrency_non_deterministic_08_select_multiple_ready_receives__emit_UnboundedSender_i64(ch: tokio::sync::mpsc::UnboundedSender<i64>, value: i64) {
    ch.send(value).unwrap();
}

#[tokio::main]
async fn main() {
    let mut __zinc_spawn_handles = Vec::new();
    let (left_tx, mut left_rx) = tokio::sync::mpsc::unbounded_channel::<i64>();
    let (right_tx, mut right_rx) = tokio::sync::mpsc::unbounded_channel::<i64>();
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = left_tx.clone(); async move { concurrency_non_deterministic_08_select_multiple_ready_receives__emit_UnboundedSender_i64(__zinc_spawn_arg_0, 1).await; } }));
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = right_tx.clone(); async move { concurrency_non_deterministic_08_select_multiple_ready_receives__emit_UnboundedSender_i64(__zinc_spawn_arg_0, 2).await; } }));
    for i in 0..2 {
        tokio::select! {
            __zinc_select_value_0_0 = async { left_rx.recv().await.unwrap() } => {
                let msg = __zinc_select_value_0_0;
                println!("left {}", msg);
            },
            __zinc_select_value_0_1 = async { right_rx.recv().await.unwrap() } => {
                let msg = __zinc_select_value_0_1;
                println!("right {}", msg);
            },
        }
    }
    while let Some(__zinc_spawn_handle) = __zinc_spawn_handles.pop() {
        __zinc_spawn_handle.await.unwrap();
    }
}