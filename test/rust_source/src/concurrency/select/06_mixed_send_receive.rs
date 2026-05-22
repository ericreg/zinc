#[tokio::main]
async fn main() {
    let (ready_tx, mut ready_rx) = tokio::sync::mpsc::unbounded_channel::<i64>();
    let (full_tx, mut full_rx) = tokio::sync::mpsc::channel::<i64>(1);
    ready_tx.send(7).unwrap();
    full_tx.send(9).await.unwrap();
    tokio::select! {
        __zinc_select_value_0_0 = async { ready_rx.recv().await.unwrap() } => {
            let msg = __zinc_select_value_0_0;
            println!("recv {}", msg);
        },
        __zinc_select_result_0_1 = full_tx.send(10) => {
            __zinc_select_result_0_1.unwrap();
            println!("send");
        },
    }
    println!("{}", full_rx.recv().await.unwrap());
}