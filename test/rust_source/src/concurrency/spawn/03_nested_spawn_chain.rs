async fn concurrency_spawn_03_nested_spawn_chain__grandchild() {
    println!("grandchild");
}

async fn concurrency_spawn_03_nested_spawn_chain__child() {
    let mut __zinc_spawn_handles = Vec::new();
    __zinc_spawn_handles.push(tokio::spawn(async move { concurrency_spawn_03_nested_spawn_chain__grandchild().await; }));
    while let Some(__zinc_spawn_handle) = __zinc_spawn_handles.pop() {
        __zinc_spawn_handle.await.unwrap();
    }
}

async fn concurrency_spawn_03_nested_spawn_chain__parent() {
    concurrency_spawn_03_nested_spawn_chain__child().await;
    println!("parent");
}

#[tokio::main]
async fn main() {
    concurrency_spawn_03_nested_spawn_chain__parent().await;
    println!("done");
}