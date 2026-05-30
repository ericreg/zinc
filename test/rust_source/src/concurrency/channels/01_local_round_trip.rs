use zinc_internal::{__ZincChannel};

#[tokio::main]
async fn main() {
    let values = __ZincChannel::<i64>::unbounded();
    values.send(5).await;
    let value = values.recv().await;
    println!("{}", value);
}