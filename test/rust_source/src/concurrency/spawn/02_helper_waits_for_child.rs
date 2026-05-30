async fn concurrency_spawn_02_helper_waits_for_child__child() {
    println!("child");
}

async fn concurrency_spawn_02_helper_waits_for_child__helper() -> i64 {
    let mut __zinc_spawn_handles = Vec::new();
    __zinc_spawn_handles.push(tokio::spawn(async move { concurrency_spawn_02_helper_waits_for_child__child().await; }));
    while let Some(__zinc_spawn_handle) = __zinc_spawn_handles.pop() {
        __zinc_spawn_handle.await.unwrap();
    }
    return 99;
}

#[tokio::main]
async fn main() {
    let value = concurrency_spawn_02_helper_waits_for_child__helper().await;
    println!("{}", value);
}