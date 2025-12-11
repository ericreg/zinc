async fn tx_chan(send_x: tokio::sync::mpsc::Sender<i64>) {
    send_x.send(1).await.unwrap();
    println!("<- 1");
    send_x.send(2).await.unwrap();
    println!("<- 2");
    send_x.send(3).await.unwrap();
    println!("<- 3");
}
#[tokio::main]
async fn main() {
    let (x_chan_tx, mut x_chan_rx) = tokio::sync::mpsc::channel::<i64>(2);
    tokio::spawn(tx_chan(x_chan_tx));
    let x = x_chan_rx.recv().await.unwrap();
    println!("{} <-", x);
    let x = x_chan_rx.recv().await.unwrap();
    println!("{} <-", x);
    let x = x_chan_rx.recv().await.unwrap();
    println!("{} <-", x);
}
