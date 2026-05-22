async fn concurrency_non_deterministic_09_bounded_backpressure_interleaving__tx_Sender(send_x: tokio::sync::mpsc::Sender<i64>) {
    send_x.send(1).await.unwrap();
    println!("<- 1");
    send_x.send(2).await.unwrap();
    println!("<- 2");
    send_x.send(3).await.unwrap();
    println!("<- 3");
}

#[tokio::main]
async fn main() {
    let mut __zinc_spawn_handles = Vec::new();
    let (x_chan_tx, mut x_chan_rx) = tokio::sync::mpsc::channel::<i64>(2);
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = x_chan_tx.clone(); async move { concurrency_non_deterministic_09_bounded_backpressure_interleaving__tx_Sender(__zinc_spawn_arg_0).await; } }));
    let mut x = x_chan_rx.recv().await.unwrap();
    println!("{} <-", x);
    x = x_chan_rx.recv().await.unwrap();
    println!("{} <-", x);
    x = x_chan_rx.recv().await.unwrap();
    println!("{} <-", x);
    while let Some(__zinc_spawn_handle) = __zinc_spawn_handles.pop() {
        __zinc_spawn_handle.await.unwrap();
    }
}