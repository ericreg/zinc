#[tokio::main]
async fn main() {
    let (values_tx, mut values_rx) = tokio::sync::mpsc::unbounded_channel::<i64>();
    values_tx.send(5).unwrap();
    let value = values_rx.recv().await.unwrap();
    println!("{}", value);
}