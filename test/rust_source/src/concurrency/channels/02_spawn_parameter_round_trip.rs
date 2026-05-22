async fn concurrency_channels_02_spawn_parameter_round_trip__tx_i64_UnboundedSender(x: i64, send_x: tokio::sync::mpsc::UnboundedSender<i64>) {
    send_x.send(x).unwrap();
}

#[tokio::main]
async fn main() {
    let mut __zinc_spawn_handles = Vec::new();
    let (x_chan_tx, mut x_chan_rx) = tokio::sync::mpsc::unbounded_channel::<i64>();
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_1 = x_chan_tx.clone(); async move { concurrency_channels_02_spawn_parameter_round_trip__tx_i64_UnboundedSender(42, __zinc_spawn_arg_1).await; } }));
    let x = x_chan_rx.recv().await.unwrap();
    println!("{}", x);
    while let Some(__zinc_spawn_handle) = __zinc_spawn_handles.pop() {
        __zinc_spawn_handle.await.unwrap();
    }
}