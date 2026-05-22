async fn concurrency_channels_04_bounded_send_unblocks__emit_Sender(values: tokio::sync::mpsc::Sender<i64>) {
    values.send(1).await.unwrap();
    values.send(2).await.unwrap();
    values.send(3).await.unwrap();
}

#[tokio::main]
async fn main() {
    let mut __zinc_spawn_handles = Vec::new();
    let (values_tx, mut values_rx) = tokio::sync::mpsc::channel::<i64>(2);
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = values_tx.clone(); async move { concurrency_channels_04_bounded_send_unblocks__emit_Sender(__zinc_spawn_arg_0).await; } }));
    println!("{}", values_rx.recv().await.unwrap());
    println!("{}", values_rx.recv().await.unwrap());
    println!("{}", values_rx.recv().await.unwrap());
    while let Some(__zinc_spawn_handle) = __zinc_spawn_handles.pop() {
        __zinc_spawn_handle.await.unwrap();
    }
}