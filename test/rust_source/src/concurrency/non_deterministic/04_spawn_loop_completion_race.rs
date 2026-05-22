async fn concurrency_non_deterministic_04_spawn_loop_completion_race__emit_i64(x: i64) {
    println!("{}", x);
}

#[tokio::main]
async fn main() {
    let mut __zinc_spawn_handles = Vec::new();
    for x in 0..5 {
        __zinc_spawn_handles.push(tokio::spawn(async move { concurrency_non_deterministic_04_spawn_loop_completion_race__emit_i64(x).await; }));
    }
    println!("done");
    while let Some(__zinc_spawn_handle) = __zinc_spawn_handles.pop() {
        __zinc_spawn_handle.await.unwrap();
    }
}