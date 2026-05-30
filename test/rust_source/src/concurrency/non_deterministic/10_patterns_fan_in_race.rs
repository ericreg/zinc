use zinc_internal::{Channel};

async fn concurrency_non_deterministic_10_patterns_fan_in_race__send_left_Channel(out: Channel<String>) {
    out.send(String::from("left")).await;
}

async fn concurrency_non_deterministic_10_patterns_fan_in_race__send_right_Channel(out: Channel<String>) {
    out.send(String::from("right")).await;
}

#[tokio::main]
async fn main() {
    let mut __zinc_spawn_handles = Vec::new();
    let left = Channel::<String>::unbounded();
    let right = Channel::<String>::unbounded();
    let merged = Channel::<String>::unbounded();
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = left.clone(); async move { concurrency_non_deterministic_10_patterns_fan_in_race__send_left_Channel(__zinc_spawn_arg_0.clone()).await; } }));
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = right.clone(); async move { concurrency_non_deterministic_10_patterns_fan_in_race__send_right_Channel(__zinc_spawn_arg_0.clone()).await; } }));
    for i in 0..2 {
        tokio::select! {
            __zinc_select_value_1_0 = async { left.recv_option().await } => {
                let msg = match __zinc_select_value_1_0 { Some(value) => value, None => panic!("select receive on closed channel") };
                merged.send(msg).await;
            },
            __zinc_select_value_1_1 = async { right.recv_option().await } => {
                let msg = match __zinc_select_value_1_1 { Some(value) => value, None => panic!("select receive on closed channel") };
                merged.send(msg).await;
            },
        }
    }
    println!("{}", merged.recv().await);
    println!("{}", merged.recv().await);
    while let Some(__zinc_spawn_handle) = __zinc_spawn_handles.pop() {
        __zinc_spawn_handle.await.unwrap();
    }
}