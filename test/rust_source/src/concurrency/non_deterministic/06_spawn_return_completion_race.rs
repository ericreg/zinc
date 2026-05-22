async fn concurrency_non_deterministic_06_spawn_return_completion_race__emit_i64(x: i64) {
    println!("{}", x);
}

async fn concurrency_non_deterministic_06_spawn_return_completion_race__launch_i64(x: i64) -> i64 {
    let mut __zinc_spawn_handles = Vec::new();
    __zinc_spawn_handles.push(tokio::spawn(async move { concurrency_non_deterministic_06_spawn_return_completion_race__emit_i64(x).await; }));
    while let Some(__zinc_spawn_handle) = __zinc_spawn_handles.pop() {
        __zinc_spawn_handle.await.unwrap();
    }
    return 99;
}

#[tokio::main]
async fn main() {
    let result = concurrency_non_deterministic_06_spawn_return_completion_race__launch_i64(5).await;
    println!("{}", result);
}