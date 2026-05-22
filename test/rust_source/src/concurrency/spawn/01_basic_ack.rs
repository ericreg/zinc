async fn concurrency_spawn_01_basic_ack__acknowledge_UnboundedSender(done: tokio::sync::mpsc::UnboundedSender<String>) {
    done.send(String::from("ok")).unwrap();
}

#[tokio::main]
async fn main() {
    let mut __zinc_spawn_handles = Vec::new();
    let (done_tx, mut done_rx) = tokio::sync::mpsc::unbounded_channel::<String>();
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = done_tx.clone(); async move { concurrency_spawn_01_basic_ack__acknowledge_UnboundedSender(__zinc_spawn_arg_0).await; } }));
    let status = done_rx.recv().await.unwrap();
    println!("{}", status);
    while let Some(__zinc_spawn_handle) = __zinc_spawn_handles.pop() {
        __zinc_spawn_handle.await.unwrap();
    }
}