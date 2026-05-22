async fn concurrency_select_05_helper_async__emit_UnboundedSender(ch: tokio::sync::mpsc::UnboundedSender<i64>) {
    ch.send(7).unwrap();
}

async fn concurrency_select_05_helper_async__helper() -> i64 {
    let mut __zinc_spawn_handles = Vec::new();
    let (values_tx, mut values_rx) = tokio::sync::mpsc::unbounded_channel::<i64>();
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = values_tx.clone(); async move { concurrency_select_05_helper_async__emit_UnboundedSender(__zinc_spawn_arg_0).await; } }));
    tokio::select! {
        __zinc_select_value_0_0 = async { values_rx.recv().await.unwrap() } => {
            let msg = __zinc_select_value_0_0;
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