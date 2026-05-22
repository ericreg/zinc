#[tokio::main]
async fn main() {
    let (ready_tx, mut ready_rx) = tokio::sync::mpsc::unbounded_channel::<i64>();
    let (blocked_tx, mut blocked_rx) = tokio::sync::mpsc::unbounded_channel::<i64>();
    blocked_tx.send(0).unwrap();
    let ignored = blocked_rx.recv().await.unwrap();
    ready_tx.send(7).unwrap();
    tokio::select! {
        __zinc_select_value_0_0 = async { ready_rx.recv().await.unwrap() } => {
            let msg = __zinc_select_value_0_0;
            println!("ready {}", msg);
        },
        __zinc_select_value_0_1 = async { blocked_rx.recv().await.unwrap() } => {
            let msg = __zinc_select_value_0_1;
            println!("blocked {}", msg);
        },
    }
}