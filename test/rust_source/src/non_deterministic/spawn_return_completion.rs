async fn emit_i64(x: i64) {
    println!("{}", x);
}

async fn launch_i64(x: i64) -> i64 {
    let mut __zinc_spawn_handles = Vec::new();
    __zinc_spawn_handles.push(tokio::spawn(async move { emit_i64(x).await; }));
    while let Some(__zinc_spawn_handle) = __zinc_spawn_handles.pop() {
        __zinc_spawn_handle.await.unwrap();
    }
    return 99;
}

#[tokio::main]
async fn main() {
    let result = launch_i64(5).await;
    println!("{}", result);
}