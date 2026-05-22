#[tokio::main]
async fn main() {
    let (primary_tx, mut primary_rx) = tokio::sync::mpsc::channel::<i64>(1);
    let (backup_tx, mut backup_rx) = tokio::sync::mpsc::channel::<i64>(1);
    primary_tx.send(1).await.unwrap();
    backup_tx.send(2).await.unwrap();
    static __ZINC_SELECT_STATE_0: std::sync::atomic::AtomicUsize = std::sync::atomic::AtomicUsize::new(0);
    let __zinc_select_start_0 = __ZINC_SELECT_STATE_0.fetch_add(1, std::sync::atomic::Ordering::Relaxed) % 2;
    '__zinc_select_0: {
        for __zinc_select_offset_0 in 0..2 {
            match (__zinc_select_start_0 + __zinc_select_offset_0) % 2 {
                0 => {
                    match primary_tx.try_send(3) {
                        Ok(()) => {
                            println!("primary");
                            break '__zinc_select_0;
                        },
                        Err(tokio::sync::mpsc::error::TrySendError::Full(_)) => {},
                        Err(tokio::sync::mpsc::error::TrySendError::Closed(_)) => panic!("select send on closed channel"),
                    }
                }
                1 => {
                    match backup_tx.try_send(4) {
                        Ok(()) => {
                            println!("backup");
                            break '__zinc_select_0;
                        },
                        Err(tokio::sync::mpsc::error::TrySendError::Full(_)) => {},
                        Err(tokio::sync::mpsc::error::TrySendError::Closed(_)) => panic!("select send on closed channel"),
                    }
                }
                _ => unreachable!(),
            }
        }
        println!("idle");
    }
    println!("{}", primary_rx.recv().await.unwrap());
    println!("{}", backup_rx.recv().await.unwrap());
}