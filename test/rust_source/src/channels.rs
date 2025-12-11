async fn tx_i64_chan(x: i64, send_x: tokio::sync::mpsc::UnboundedSender<i64>) {
    send_x.send(x).unwrap();
}
#[tokio::main]
async fn main() {
    let (x_chan_tx, mut x_chan_rx) = tokio::sync::mpsc::unbounded_channel::<i64>();
    tokio::spawn(tx_i64_chan(42, x_chan_tx));
    let x = x_chan_rx.recv().await.unwrap();
    println!("{}", x);
}
