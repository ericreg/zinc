use zinc_internal::{__ZincChannel};

async fn concurrency_non_deterministic_08_select_multiple_ready_receives__emit_Channel_i64(ch: __ZincChannel<i64>, value: i64) {
    ch.send(value).await;
}

#[tokio::main]
async fn main() {
    let mut __zinc_spawn_handles = Vec::new();
    let left = __ZincChannel::<i64>::unbounded();
    let right = __ZincChannel::<i64>::unbounded();
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = left.clone(); async move { concurrency_non_deterministic_08_select_multiple_ready_receives__emit_Channel_i64(__zinc_spawn_arg_0.clone(), 1).await; } }));
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = right.clone(); async move { concurrency_non_deterministic_08_select_multiple_ready_receives__emit_Channel_i64(__zinc_spawn_arg_0.clone(), 2).await; } }));
    for i in 0..2 {
        tokio::select! {
            __zinc_select_value_1_0 = async { left.recv_option().await } => {
                let msg = match __zinc_select_value_1_0 { Some(value) => value, None => panic!("select receive on closed channel") };
                println!("left {}", msg);
            },
            __zinc_select_value_1_1 = async { right.recv_option().await } => {
                let msg = match __zinc_select_value_1_1 { Some(value) => value, None => panic!("select receive on closed channel") };
                println!("right {}", msg);
            },
        }
    }
    while let Some(__zinc_spawn_handle) = __zinc_spawn_handles.pop() {
        __zinc_spawn_handle.await.unwrap();
    }
}