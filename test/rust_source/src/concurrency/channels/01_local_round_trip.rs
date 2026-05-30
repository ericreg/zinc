use zinc_internal::{Channel};

#[tokio::main]
async fn main() {
    let values = Channel::<i64>::unbounded();
    values.send(5).await;
    let value = values.recv().await;
    println!("{}", value);
}