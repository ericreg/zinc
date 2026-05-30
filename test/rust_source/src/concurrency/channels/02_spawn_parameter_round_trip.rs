use zinc_internal::{Channel};

async fn concurrency_channels_02_spawn_parameter_round_trip__tx_i64_Channel(x: i64, send_x: Channel<i64>) {
    send_x.send(x).await;
}

#[tokio::main]
async fn main() {
    let mut __zinc_spawn_handles = Vec::new();
    let x_chan = Channel::<i64>::unbounded();
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_1 = x_chan.clone(); async move { concurrency_channels_02_spawn_parameter_round_trip__tx_i64_Channel(42, __zinc_spawn_arg_1.clone()).await; } }));
    let x = x_chan.recv().await;
    println!("{}", x);
    while let Some(__zinc_spawn_handle) = __zinc_spawn_handles.pop() {
        __zinc_spawn_handle.await.unwrap();
    }
}