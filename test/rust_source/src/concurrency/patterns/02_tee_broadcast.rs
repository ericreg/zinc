use zinc_internal::{__ZincChannel};

async fn concurrency_patterns_02_tee_broadcast__source_Channel(out: __ZincChannel<i64>) {
    out.send(3).await;
}

#[tokio::main]
async fn main() {
    let mut __zinc_spawn_handles = Vec::new();
    let input = __ZincChannel::<i64>::unbounded();
    let left = __ZincChannel::<i64>::unbounded();
    let right = __ZincChannel::<i64>::unbounded();
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = input.clone(); async move { concurrency_patterns_02_tee_broadcast__source_Channel(__zinc_spawn_arg_0.clone()).await; } }));
    let value = input.recv().await;
    left.send(value).await;
    right.send(value).await;
    println!("{}", left.recv().await);
    println!("{}", right.recv().await);
    while let Some(__zinc_spawn_handle) = __zinc_spawn_handles.pop() {
        __zinc_spawn_handle.await.unwrap();
    }
}