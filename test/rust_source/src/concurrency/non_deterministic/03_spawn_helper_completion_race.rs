async fn concurrency_non_deterministic_03_spawn_helper_completion_race__emit_i64(x: i64) {
    println!("{}", x);
}

async fn concurrency_non_deterministic_03_spawn_helper_completion_race__launch_i64(x: i64) {
    let mut __zinc_spawn_handles = Vec::new();
    __zinc_spawn_handles.push(tokio::spawn(async move { concurrency_non_deterministic_03_spawn_helper_completion_race__emit_i64(x).await; }));
    println!("launched");
    while let Some(__zinc_spawn_handle) = __zinc_spawn_handles.pop() {
        __zinc_spawn_handle.await.unwrap();
    }
}

#[tokio::main]
async fn main() {
    concurrency_non_deterministic_03_spawn_helper_completion_race__launch_i64(7).await;
    println!("done");
}