async fn concurrency_patterns_03_request_reply__respond_UnboundedSender_i64(reply: tokio::sync::mpsc::UnboundedSender<i64>, request: i64) {
    reply.send((request + 1)).unwrap();
}

#[tokio::main]
async fn main() {
    let mut __zinc_spawn_handles = Vec::new();
    let (reply_tx, mut reply_rx) = tokio::sync::mpsc::unbounded_channel::<i64>();
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = reply_tx.clone(); async move { concurrency_patterns_03_request_reply__respond_UnboundedSender_i64(__zinc_spawn_arg_0, 41).await; } }));
    let response = reply_rx.recv().await.unwrap();
    println!("{}", response);
    while let Some(__zinc_spawn_handle) = __zinc_spawn_handles.pop() {
        __zinc_spawn_handle.await.unwrap();
    }
}