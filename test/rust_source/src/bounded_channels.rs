fn tx_chan(send_x: chan) {
    send_x.send(1).unwrap();
    println!("<- 1");
    send_x.send(2).unwrap();
    println!("<- 2");
    send_x.send(3).unwrap();
    println!("<- 3");
}

#[tokio::main]
async fn main() {
    let x_chan = chan(2);
    tokio::spawn(tx_chan(x_chan));
    let x = x_chan.recv().await.unwrap();
    println!("{} <-", x);
    x = x_chan.recv().await.unwrap();
    println!("{} <-", x);
    x = x_chan.recv().await.unwrap();
    println!("{} <-", x);
}