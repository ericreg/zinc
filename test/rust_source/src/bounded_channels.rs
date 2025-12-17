async fn tx_chan(send_x: tokio::sync::mpsc::UnboundedSender<i64>) {
    send_x.send(1).unwrap();
    println!("<- 1");
    send_x.send(2).unwrap();
    println!("<- 2");
    send_x.send(3).unwrap();
    println!("<- 3");
}

#[tokio::main]
async fn main() {
    let (x_chan_tx, mut x_chan_rx) = tokio::sync::mpsc::unbounded_channel::<i64>();
    tokio::spawn(tx_chan(x_chan_tx));
    let mut x = x_chan_rx.recv().await.unwrap();
    println!("{} <-", x);
    x = x_chan_rx.recv().await.unwrap();
    println!("{} <-", x);
    x = x_chan_rx.recv().await.unwrap();
    println!("{} <-", x);
}