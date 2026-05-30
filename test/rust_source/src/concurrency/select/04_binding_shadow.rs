use zinc_internal::{__ZincChannel};

async fn concurrency_select_04_binding_shadow__emit_Channel(ch: __ZincChannel<String>) {
    ch.send(String::from("inner")).await;
}

#[tokio::main]
async fn main() {
    let mut __zinc_spawn_handles = Vec::new();
    let value = "outer";
    let values = __ZincChannel::<String>::unbounded();
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = values.clone(); async move { concurrency_select_04_binding_shadow__emit_Channel(__zinc_spawn_arg_0.clone()).await; } }));
    tokio::select! {
        __zinc_select_value_0_0 = async { values.recv_option().await } => {
            let value = match __zinc_select_value_0_0 { Some(value) => value, None => panic!("select receive on closed channel") };
            println!("{}", value);
        },
    }
    println!("{}", value);
    while let Some(__zinc_spawn_handle) = __zinc_spawn_handles.pop() {
        __zinc_spawn_handle.await.unwrap();
    }
}