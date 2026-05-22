async fn concurrency_non_deterministic_10_patterns_fan_in_race__send_left_UnboundedSender(out: tokio::sync::mpsc::UnboundedSender<String>) {
    out.send(String::from("left")).unwrap();
}

async fn concurrency_non_deterministic_10_patterns_fan_in_race__send_right_UnboundedSender(out: tokio::sync::mpsc::UnboundedSender<String>) {
    out.send(String::from("right")).unwrap();
}

#[tokio::main]
async fn main() {
    let mut __zinc_spawn_handles = Vec::new();
    let (left_tx, mut left_rx) = tokio::sync::mpsc::unbounded_channel::<String>();
    let (right_tx, mut right_rx) = tokio::sync::mpsc::unbounded_channel::<String>();
    let (merged_tx, mut merged_rx) = tokio::sync::mpsc::unbounded_channel::<String>();
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = left_tx.clone(); async move { concurrency_non_deterministic_10_patterns_fan_in_race__send_left_UnboundedSender(__zinc_spawn_arg_0).await; } }));
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = right_tx.clone(); async move { concurrency_non_deterministic_10_patterns_fan_in_race__send_right_UnboundedSender(__zinc_spawn_arg_0).await; } }));
    for i in 0..2 {
        tokio::select! {
            __zinc_select_value_0_0 = async { left_rx.recv().await.unwrap() } => {
                let msg = __zinc_select_value_0_0;
                merged_tx.send(msg.to_string()).unwrap();
            },
            __zinc_select_value_0_1 = async { right_rx.recv().await.unwrap() } => {
                let msg = __zinc_select_value_0_1;
                merged_tx.send(msg.to_string()).unwrap();
            },
        }
    }
    println!("{}", merged_rx.recv().await.unwrap());
    println!("{}", merged_rx.recv().await.unwrap());
    while let Some(__zinc_spawn_handle) = __zinc_spawn_handles.pop() {
        __zinc_spawn_handle.await.unwrap();
    }
}