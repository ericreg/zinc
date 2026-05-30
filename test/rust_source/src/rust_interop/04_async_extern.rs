use tokio::task::yield_now;

#[tokio::main]
async fn main() {
    yield_now().await;
    println!("done");
}