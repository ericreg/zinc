use zinc_internal::{Channel};

async fn concurrency_patterns_03_request_reply__respond_Channel_i64(reply: Channel<i64>, request: i64) {
    reply.send((request + 1)).await;
}

#[tokio::main]
async fn main() {
    let mut __zinc_spawn_handles = Vec::new();
    let reply = Channel::<i64>::unbounded();
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = reply.clone(); async move { concurrency_patterns_03_request_reply__respond_Channel_i64(__zinc_spawn_arg_0.clone(), 41).await; } }));
    let response = reply.recv().await;
    println!("{}", response);
    while let Some(__zinc_spawn_handle) = __zinc_spawn_handles.pop() {
        __zinc_spawn_handle.await.unwrap();
    }
}