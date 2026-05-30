use zinc_internal::{Channel};

async fn concurrency_channels_07_param_receive_send__bounce_Channel_Channel(input: Channel<i64>, output: Channel<i64>) {
    let value = input.recv().await;
    output.send((value + 1)).await;
    output.close();
}

#[tokio::main]
async fn main() {
    let mut __zinc_spawn_handles = Vec::new();
    let input = Channel::<i64>::unbounded();
    let output = Channel::<i64>::unbounded();
    input.send(4).await;
    input.close();
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = input.clone(); let __zinc_spawn_arg_1 = output.clone(); async move { concurrency_channels_07_param_receive_send__bounce_Channel_Channel(__zinc_spawn_arg_0.clone(), __zinc_spawn_arg_1.clone()).await; } }));
    println!("{}", output.recv().await);
    while let Some(__zinc_spawn_handle) = __zinc_spawn_handles.pop() {
        __zinc_spawn_handle.await.unwrap();
    }
}