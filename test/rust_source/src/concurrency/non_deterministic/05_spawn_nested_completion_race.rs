async fn concurrency_non_deterministic_05_spawn_nested_completion_race__child_i64(x: i64) {
    println!("{}", x);
}

async fn concurrency_non_deterministic_05_spawn_nested_completion_race__parent_i64(x: i64) {
    let mut __zinc_spawn_handles = Vec::new();
    __zinc_spawn_handles.push(tokio::spawn(async move { concurrency_non_deterministic_05_spawn_nested_completion_race__child_i64((x + 1)).await; }));
    println!("{}", x);
    while let Some(__zinc_spawn_handle) = __zinc_spawn_handles.pop() {
        __zinc_spawn_handle.await.unwrap();
    }
}

#[tokio::main]
async fn main() {
    let mut __zinc_spawn_handles = Vec::new();
    __zinc_spawn_handles.push(tokio::spawn(async move { concurrency_non_deterministic_05_spawn_nested_completion_race__parent_i64(10).await; }));
    println!("done");
    while let Some(__zinc_spawn_handle) = __zinc_spawn_handles.pop() {
        __zinc_spawn_handle.await.unwrap();
    }
}