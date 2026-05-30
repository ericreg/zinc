use zinc_internal::{Channel};

#[tokio::main]
async fn main() {
    let ready = Channel::<i64>::unbounded();
    let blocked = Channel::<i64>::unbounded();
    blocked.send(0).await;
    let ignored = blocked.recv().await;
    ready.send(7).await;
    tokio::select! {
        __zinc_select_value_0_0 = async { ready.recv_option().await } => {
            let msg = match __zinc_select_value_0_0 { Some(value) => value, None => panic!("select receive on closed channel") };
            println!("ready {}", msg);
        },
        __zinc_select_value_0_1 = async { blocked.recv_option().await } => {
            let msg = match __zinc_select_value_0_1 { Some(value) => value, None => panic!("select receive on closed channel") };
            println!("blocked {}", msg);
        },
    }
}