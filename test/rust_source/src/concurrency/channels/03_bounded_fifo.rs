use zinc_internal::{Channel};

#[tokio::main]
async fn main() {
    let values = Channel::<i64>::bounded(3);
    values.send(1).await;
    values.send(2).await;
    values.send(3).await;
    println!("{}", values.recv().await);
    println!("{}", values.recv().await);
    println!("{}", values.recv().await);
}