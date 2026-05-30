use zinc_internal::{__ZincChannel};

async fn concurrency_channels_04_bounded_send_unblocks__emit_BoundedChannel(values: __ZincChannel<i64>) {
    values.send(1).await;
    values.send(2).await;
    values.send(3).await;
}

#[tokio::main]
async fn main() {
    let mut __zinc_spawn_handles = Vec::new();
    let values = __ZincChannel::<i64>::bounded(2);
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = values.clone(); async move { concurrency_channels_04_bounded_send_unblocks__emit_BoundedChannel(__zinc_spawn_arg_0.clone()).await; } }));
    println!("{}", values.recv().await);
    println!("{}", values.recv().await);
    println!("{}", values.recv().await);
    while let Some(__zinc_spawn_handle) = __zinc_spawn_handles.pop() {
        __zinc_spawn_handle.await.unwrap();
    }
}