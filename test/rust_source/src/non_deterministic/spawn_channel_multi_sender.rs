async fn non_deterministic_spawn_channel_multi_sender__send_value_chan_i64(ch: tokio::sync::mpsc::UnboundedSender<i64>, x: i64) {
    ch.send(x).unwrap();
    println!("sent {}", x);
}

#[tokio::main]
async fn main() {
    let mut __zinc_spawn_handles = Vec::new();
    let (values_tx, mut values_rx) = tokio::sync::mpsc::unbounded_channel::<i64>();
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = values_tx.clone(); async move { non_deterministic_spawn_channel_multi_sender__send_value_chan_i64(__zinc_spawn_arg_0, 1).await; } }));
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = values_tx.clone(); async move { non_deterministic_spawn_channel_multi_sender__send_value_chan_i64(__zinc_spawn_arg_0, 2).await; } }));
    let a = values_rx.recv().await.unwrap();
    let b = values_rx.recv().await.unwrap();
    println!("got {}", a);
    println!("got {}", b);
    while let Some(__zinc_spawn_handle) = __zinc_spawn_handles.pop() {
        __zinc_spawn_handle.await.unwrap();
    }
}