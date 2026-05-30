use zinc_internal::{__ZincChannel};

async fn concurrency_spawn_01_basic_ack__acknowledge_Channel(done: __ZincChannel<String>) {
    done.send(String::from("ok")).await;
}

#[tokio::main]
async fn main() {
    let mut __zinc_spawn_handles = Vec::new();
    let done = __ZincChannel::<String>::unbounded();
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = done.clone(); async move { concurrency_spawn_01_basic_ack__acknowledge_Channel(__zinc_spawn_arg_0.clone()).await; } }));
    let status = done.recv().await;
    println!("{}", status);
    while let Some(__zinc_spawn_handle) = __zinc_spawn_handles.pop() {
        __zinc_spawn_handle.await.unwrap();
    }
}