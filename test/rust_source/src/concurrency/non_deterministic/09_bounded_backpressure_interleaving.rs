use zinc_internal::{Channel};

async fn concurrency_non_deterministic_09_bounded_backpressure_interleaving__tx_BoundedChannel(send_x: Channel<i64>) {
    send_x.send(1).await;
    println!("<- 1");
    send_x.send(2).await;
    println!("<- 2");
    send_x.send(3).await;
    println!("<- 3");
}

#[tokio::main]
async fn main() {
    let mut __zinc_spawn_handles = Vec::new();
    let x_chan = Channel::<i64>::bounded(2);
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = x_chan.clone(); async move { concurrency_non_deterministic_09_bounded_backpressure_interleaving__tx_BoundedChannel(__zinc_spawn_arg_0.clone()).await; } }));
    let mut x = x_chan.recv().await;
    println!("{} <-", x);
    x = x_chan.recv().await;
    println!("{} <-", x);
    x = x_chan.recv().await;
    println!("{} <-", x);
    while let Some(__zinc_spawn_handle) = __zinc_spawn_handles.pop() {
        __zinc_spawn_handle.await.unwrap();
    }
}