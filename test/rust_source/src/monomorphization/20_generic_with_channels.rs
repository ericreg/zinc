async fn double_sender_chan_i64(ch: tokio::sync::mpsc::UnboundedSender<i64>, val: i64) {
    ch.send(val).unwrap();
    ch.send(val).unwrap();
}

async fn sender_chan_i64(ch: tokio::sync::mpsc::UnboundedSender<i64>, val: i64) {
    ch.send(val).unwrap();
}

#[tokio::main]
async fn main() {
    let (int_ch_tx, mut int_ch_rx) = tokio::sync::mpsc::unbounded_channel::<i64>();
    tokio::spawn(sender_chan_i64(int_ch_tx, 42));
    let x = int_ch_rx.recv().await.unwrap();
    println!("received int: {}", x);
    let (int_ch2_tx, mut int_ch2_rx) = tokio::sync::mpsc::unbounded_channel::<i64>();
    tokio::spawn(double_sender_chan_i64(int_ch2_tx, 100));
    let y1 = int_ch2_rx.recv().await.unwrap();
    let y2 = int_ch2_rx.recv().await.unwrap();
    println!("double received: {}, {}", y1, y2);
    let (int_ch3_tx, mut int_ch3_rx) = tokio::sync::mpsc::unbounded_channel::<i64>();
    tokio::spawn(sender_chan_i64(int_ch3_tx, 999));
    let z = int_ch3_rx.recv().await.unwrap();
    println!("received another int: {}", z);
}