use zinc_internal::{__ZincChannel};

async fn monomorphization_20_generic_with_channels__double_sender_Channel_i64(ch: __ZincChannel<i64>, val: i64) {
    ch.send(val).await;
    ch.send(val).await;
}

async fn monomorphization_20_generic_with_channels__sender_Channel_i64(ch: __ZincChannel<i64>, val: i64) {
    ch.send(val).await;
}

#[tokio::main]
async fn main() {
    let mut __zinc_spawn_handles = Vec::new();
    let int_ch = __ZincChannel::<i64>::unbounded();
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = int_ch.clone(); async move { monomorphization_20_generic_with_channels__sender_Channel_i64(__zinc_spawn_arg_0.clone(), 42).await; } }));
    let x = int_ch.recv().await;
    println!("received int: {}", x);
    let int_ch2 = __ZincChannel::<i64>::unbounded();
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = int_ch2.clone(); async move { monomorphization_20_generic_with_channels__double_sender_Channel_i64(__zinc_spawn_arg_0.clone(), 100).await; } }));
    let y1 = int_ch2.recv().await;
    let y2 = int_ch2.recv().await;
    println!("double received: {}, {}", y1, y2);
    let int_ch3 = __ZincChannel::<i64>::unbounded();
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = int_ch3.clone(); async move { monomorphization_20_generic_with_channels__sender_Channel_i64(__zinc_spawn_arg_0.clone(), 999).await; } }));
    let z = int_ch3.recv().await;
    println!("received another int: {}", z);
    while let Some(__zinc_spawn_handle) = __zinc_spawn_handles.pop() {
        __zinc_spawn_handle.await.unwrap();
    }
}