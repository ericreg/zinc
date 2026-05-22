#[tokio::main]
async fn main() {
    let (primary_tx, mut primary_rx) = tokio::sync::mpsc::channel::<i64>(1);
    let (backup_tx, mut backup_rx) = tokio::sync::mpsc::channel::<i64>(1);
    primary_tx.send(1).await.unwrap();
    tokio::select! {
        __zinc_select_result_0_0 = primary_tx.send(2) => {
            __zinc_select_result_0_0.unwrap();
            println!("primary");
        },
        __zinc_select_result_0_1 = backup_tx.send(3) => {
            __zinc_select_result_0_1.unwrap();
            println!("backup");
        },
    }
    println!("{}", primary_rx.recv().await.unwrap());
    println!("{}", backup_rx.recv().await.unwrap());
}