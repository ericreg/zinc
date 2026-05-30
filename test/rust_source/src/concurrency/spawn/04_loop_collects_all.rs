use zinc_internal::{Channel};

async fn concurrency_spawn_04_loop_collects_all__emit_Channel_i64(results: Channel<i64>, value: i64) {
    results.send(value).await;
}

#[tokio::main]
async fn main() {
    let mut __zinc_spawn_handles = Vec::new();
    let results = Channel::<i64>::unbounded();
    for i in 1..=4 {
        __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = results.clone(); async move { concurrency_spawn_04_loop_collects_all__emit_Channel_i64(__zinc_spawn_arg_0.clone(), i).await; } }));
    }
    let mut total = 0;
    for i in 0..4 {
        let value = results.recv().await;
        total = (total + value);
    }
    println!("{}", total);
    while let Some(__zinc_spawn_handle) = __zinc_spawn_handles.pop() {
        __zinc_spawn_handle.await.unwrap();
    }
}