#[tokio::main]
async fn main() {
    let (values_tx, mut values_rx) = tokio::sync::mpsc::channel::<i64>(3);
    values_tx.send(1).await.unwrap();
    values_tx.send(2).await.unwrap();
    values_tx.send(3).await.unwrap();
    println!("{}", values_rx.recv().await.unwrap());
    println!("{}", values_rx.recv().await.unwrap());
    println!("{}", values_rx.recv().await.unwrap());
}