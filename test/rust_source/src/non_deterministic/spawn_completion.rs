async fn non_deterministic_spawn_completion__emit_i64(x: i64) {
    println!("{}", x);
}

#[tokio::main]
async fn main() {
    let mut __zinc_spawn_handles = Vec::new();
    __zinc_spawn_handles.push(tokio::spawn(async move { non_deterministic_spawn_completion__emit_i64(1).await; }));
    __zinc_spawn_handles.push(tokio::spawn(async move { non_deterministic_spawn_completion__emit_i64(2).await; }));
    println!("done");
    while let Some(__zinc_spawn_handle) = __zinc_spawn_handles.pop() {
        __zinc_spawn_handle.await.unwrap();
    }
}