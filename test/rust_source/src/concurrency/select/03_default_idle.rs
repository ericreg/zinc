use zinc_internal::{Channel, TrySend};

#[tokio::main]
async fn main() {
    let primary = Channel::<i64>::bounded(1);
    let backup = Channel::<i64>::bounded(1);
    primary.send(1).await;
    backup.send(2).await;
    static __ZINC_SELECT_STATE_0: std::sync::atomic::AtomicUsize = std::sync::atomic::AtomicUsize::new(0);
    let __zinc_select_start_0 = __ZINC_SELECT_STATE_0.fetch_add(1, std::sync::atomic::Ordering::Relaxed) % 2;
    '__zinc_select_0: {
        for __zinc_select_offset_0 in 0..2 {
            match (__zinc_select_start_0 + __zinc_select_offset_0) % 2 {
                0 => {
                    match primary.try_send(3) {
                        TrySend::Sent => {
                            println!("primary");
                            break '__zinc_select_0;
                        },
                        TrySend::Full(_) => {},
                        TrySend::Closed(_) => panic!("select send on closed channel"),
                    }
                }
                1 => {
                    match backup.try_send(4) {
                        TrySend::Sent => {
                            println!("backup");
                            break '__zinc_select_0;
                        },
                        TrySend::Full(_) => {},
                        TrySend::Closed(_) => panic!("select send on closed channel"),
                    }
                }
                _ => unreachable!(),
            }
        }
        println!("idle");
    }
    println!("{}", primary.recv().await);
    println!("{}", backup.recv().await);
}