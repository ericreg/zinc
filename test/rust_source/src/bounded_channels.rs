async fn bounded_channels__tx_chan(send_x: tokio::sync::mpsc::UnboundedSender<i64>) {
    send_x.send(1).unwrap();
    println!("<- 1");
    send_x.send(2).unwrap();
    println!("<- 2");
    send_x.send(3).unwrap();
    println!("<- 3");
}

#[tokio::main]
async fn main() {
    let mut __zinc_spawn_handles = Vec::new();
    let (x_chan_tx, mut x_chan_rx) = tokio::sync::mpsc::unbounded_channel::<i64>();
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = x_chan_tx.clone(); async move { bounded_channels__tx_chan(__zinc_spawn_arg_0).await; } }));
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