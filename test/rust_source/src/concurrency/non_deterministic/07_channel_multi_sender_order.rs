use zinc_internal::{Channel};

async fn concurrency_non_deterministic_07_channel_multi_sender_order__send_value_Channel_i64(ch: Channel<i64>, x: i64) {
    ch.send(x).await;
    println!("sent {}", x);
}

#[tokio::main]
async fn main() {
    let mut __zinc_spawn_handles = Vec::new();
    let values = Channel::<i64>::unbounded();
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = values.clone(); async move { concurrency_non_deterministic_07_channel_multi_sender_order__send_value_Channel_i64(__zinc_spawn_arg_0.clone(), 1).await; } }));
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = values.clone(); async move { concurrency_non_deterministic_07_channel_multi_sender_order__send_value_Channel_i64(__zinc_spawn_arg_0.clone(), 2).await; } }));
    let a = values.recv().await;
    let b = values.recv().await;
    println!("got {}", a);
    println!("got {}", b);
    while let Some(__zinc_spawn_handle) = __zinc_spawn_handles.pop() {
        __zinc_spawn_handle.await.unwrap();
    }
}