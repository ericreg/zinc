async fn tx_i64_chan(x: i64, send_x: chan) {
    send_x.send(x).unwrap();
}

#[tokio::main]
async fn main() {
    let x_chan = chan();
    tokio::spawn(tx_i64_chan(42, x_chan));
    let x = x_chan.recv().await.unwrap();
    println!("{}", x);
}