use zinc_internal::{__ZincChannel};

async fn concurrency_patterns_06_fan_out_coordinated__double_Channel_i64(out: __ZincChannel<i64>, value: i64) {
    out.send((value * 2)).await;
}

async fn concurrency_patterns_06_fan_out_coordinated__triple_Channel_i64(out: __ZincChannel<i64>, value: i64) {
    out.send((value * 3)).await;
}

#[tokio::main]
async fn main() {
    let mut __zinc_spawn_handles = Vec::new();
    let doubles = __ZincChannel::<i64>::unbounded();
    let triples = __ZincChannel::<i64>::unbounded();
    let source = 5;
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = doubles.clone(); async move { concurrency_patterns_06_fan_out_coordinated__double_Channel_i64(__zinc_spawn_arg_0.clone(), source).await; } }));
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = triples.clone(); async move { concurrency_patterns_06_fan_out_coordinated__triple_Channel_i64(__zinc_spawn_arg_0.clone(), source).await; } }));
    println!("{}", doubles.recv().await);
    println!("{}", triples.recv().await);
    while let Some(__zinc_spawn_handle) = __zinc_spawn_handles.pop() {
        __zinc_spawn_handle.await.unwrap();
    }
}