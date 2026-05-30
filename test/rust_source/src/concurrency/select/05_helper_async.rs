use zinc_internal::{__ZincChannel};

async fn concurrency_select_05_helper_async__emit_Channel(ch: __ZincChannel<i64>) {
    ch.send(7).await;
}

async fn concurrency_select_05_helper_async__helper() -> i64 {
    let mut __zinc_spawn_handles = Vec::new();
    let values = __ZincChannel::<i64>::unbounded();
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = values.clone(); async move { concurrency_select_05_helper_async__emit_Channel(__zinc_spawn_arg_0.clone()).await; } }));
    tokio::select! {
        __zinc_select_value_0_0 = async { values.recv_option().await } => {
            let msg = match __zinc_select_value_0_0 { Some(value) => value, None => panic!("select receive on closed channel") };
            while let Some(__zinc_spawn_handle) = __zinc_spawn_handles.pop() {
                __zinc_spawn_handle.await.unwrap();
            }
            return msg;
        },
    }
}

#[tokio::main]
async fn main() {
    let result = concurrency_select_05_helper_async__helper().await;
    println!("{}", result);
}