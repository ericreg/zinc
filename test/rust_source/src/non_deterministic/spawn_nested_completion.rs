async fn non_deterministic_spawn_nested_completion__child_i64(x: i64) {
    println!("{}", x);
}

async fn non_deterministic_spawn_nested_completion__parent_i64(x: i64) {
    let mut __zinc_spawn_handles = Vec::new();
    __zinc_spawn_handles.push(tokio::spawn(async move { non_deterministic_spawn_nested_completion__child_i64((x + 1)).await; }));
    println!("{}", x);
    while let Some(__zinc_spawn_handle) = __zinc_spawn_handles.pop() {
        __zinc_spawn_handle.await.unwrap();
    }
}

#[tokio::main]
async fn main() {
    let mut __zinc_spawn_handles = Vec::new();
    __zinc_spawn_handles.push(tokio::spawn(async move { non_deterministic_spawn_nested_completion__parent_i64(10).await; }));
    println!("done");
    while let Some(__zinc_spawn_handle) = __zinc_spawn_handles.pop() {
        __zinc_spawn_handle.await.unwrap();
    }
}