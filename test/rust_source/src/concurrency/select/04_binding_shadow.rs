async fn concurrency_select_04_binding_shadow__emit_UnboundedSender(ch: tokio::sync::mpsc::UnboundedSender<String>) {
    ch.send(String::from("inner")).unwrap();
}

#[tokio::main]
async fn main() {
    let mut __zinc_spawn_handles = Vec::new();
    let value = "outer";
    let (values_tx, mut values_rx) = tokio::sync::mpsc::unbounded_channel::<String>();
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = values_tx.clone(); async move { concurrency_select_04_binding_shadow__emit_UnboundedSender(__zinc_spawn_arg_0).await; } }));
    tokio::select! {
        __zinc_select_value_0_0 = async { values_rx.recv().await.unwrap() } => {
            let value = __zinc_select_value_0_0;
            println!("{}", value);
        },
    }
    println!("{}", value);
    while let Some(__zinc_spawn_handle) = __zinc_spawn_handles.pop() {
        __zinc_spawn_handle.await.unwrap();
    }
}