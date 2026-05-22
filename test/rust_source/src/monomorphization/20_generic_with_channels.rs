async fn monomorphization_20_generic_with_channels__double_sender_chan_i64(ch: tokio::sync::mpsc::UnboundedSender<i64>, val: i64) {
    ch.send(val).unwrap();
    ch.send(val).unwrap();
}

async fn monomorphization_20_generic_with_channels__sender_chan_i64(ch: tokio::sync::mpsc::UnboundedSender<i64>, val: i64) {
    ch.send(val).unwrap();
}

#[tokio::main]
async fn main() {
    let mut __zinc_spawn_handles = Vec::new();
    let (int_ch_tx, mut int_ch_rx) = tokio::sync::mpsc::unbounded_channel::<i64>();
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = int_ch_tx.clone(); async move { monomorphization_20_generic_with_channels__sender_chan_i64(__zinc_spawn_arg_0, 42).await; } }));
    let x = int_ch_rx.recv().await.unwrap();
    println!("received int: {}", x);
    let (int_ch2_tx, mut int_ch2_rx) = tokio::sync::mpsc::unbounded_channel::<i64>();
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = int_ch2_tx.clone(); async move { monomorphization_20_generic_with_channels__double_sender_chan_i64(__zinc_spawn_arg_0, 100).await; } }));
    let y1 = int_ch2_rx.recv().await.unwrap();
    let y2 = int_ch2_rx.recv().await.unwrap();
    println!("double received: {}, {}", y1, y2);
    let (int_ch3_tx, mut int_ch3_rx) = tokio::sync::mpsc::unbounded_channel::<i64>();
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = int_ch3_tx.clone(); async move { monomorphization_20_generic_with_channels__sender_chan_i64(__zinc_spawn_arg_0, 999).await; } }));
    let z = int_ch3_rx.recv().await.unwrap();
    println!("received another int: {}", z);
    while let Some(__zinc_spawn_handle) = __zinc_spawn_handles.pop() {
        __zinc_spawn_handle.await.unwrap();
    }
}