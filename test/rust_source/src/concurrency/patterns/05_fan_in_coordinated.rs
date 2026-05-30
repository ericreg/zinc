use zinc_internal::{__ZincChannel};

async fn concurrency_patterns_05_fan_in_coordinated__send_left_Channel(out: __ZincChannel<i64>) {
    out.send(1).await;
}

async fn concurrency_patterns_05_fan_in_coordinated__send_right_Channel(out: __ZincChannel<i64>) {
    out.send(2).await;
}

#[tokio::main]
async fn main() {
    let mut __zinc_spawn_handles = Vec::new();
    let left = __ZincChannel::<i64>::unbounded();
    let right = __ZincChannel::<i64>::unbounded();
    let merged = __ZincChannel::<i64>::unbounded();
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = left.clone(); async move { concurrency_patterns_05_fan_in_coordinated__send_left_Channel(__zinc_spawn_arg_0.clone()).await; } }));
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = right.clone(); async move { concurrency_patterns_05_fan_in_coordinated__send_right_Channel(__zinc_spawn_arg_0.clone()).await; } }));
    let left_value = left.recv().await;
    let right_value = right.recv().await;
    merged.send(left_value).await;
    merged.send(right_value).await;
    println!("{}", merged.recv().await);
    println!("{}", merged.recv().await);
    while let Some(__zinc_spawn_handle) = __zinc_spawn_handles.pop() {
        __zinc_spawn_handle.await.unwrap();
    }
}