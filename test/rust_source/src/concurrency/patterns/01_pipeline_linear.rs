use zinc_internal::{Channel};

async fn concurrency_patterns_01_pipeline_linear__source_Channel(out: Channel<i64>) {
    out.send(5).await;
}

#[tokio::main]
async fn main() {
    let mut __zinc_spawn_handles = Vec::new();
    let stage1 = Channel::<i64>::unbounded();
    let stage2 = Channel::<i64>::unbounded();
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = stage1.clone(); async move { concurrency_patterns_01_pipeline_linear__source_Channel(__zinc_spawn_arg_0.clone()).await; } }));
    let value = stage1.recv().await;
    stage2.send((value * 2)).await;
    let result = stage2.recv().await;
    println!("{}", result);
    while let Some(__zinc_spawn_handle) = __zinc_spawn_handles.pop() {
        __zinc_spawn_handle.await.unwrap();
    }
}