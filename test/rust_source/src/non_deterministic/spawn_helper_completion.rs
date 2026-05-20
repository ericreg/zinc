async fn emit_i64(x: i64) {
    println!("{}", x);
}

async fn launch_i64(x: i64) {
    let mut __zinc_spawn_handles = Vec::new();
    __zinc_spawn_handles.push(tokio::spawn(async move { emit_i64(x).await; }));
    println!("launched");
    while let Some(__zinc_spawn_handle) = __zinc_spawn_handles.pop() {
        __zinc_spawn_handle.await.unwrap();
    }
}

#[tokio::main]
async fn main() {
    launch_i64(7).await;
    println!("done");
}