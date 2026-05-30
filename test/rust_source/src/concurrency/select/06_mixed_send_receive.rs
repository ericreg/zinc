use zinc_internal::{__ZincChannel};

#[tokio::main]
async fn main() {
    let ready = __ZincChannel::<i64>::unbounded();
    let full = __ZincChannel::<i64>::bounded(1);
    ready.send(7).await;
    full.send(9).await;
    tokio::select! {
        __zinc_select_value_0_0 = async { ready.recv_option().await } => {
            let msg = match __zinc_select_value_0_0 { Some(value) => value, None => panic!("select receive on closed channel") };
            println!("recv {}", msg);
        },
        __zinc_select_result_0_1 = async { full.send(10).await } => {
            println!("send");
        },
    }
    println!("{}", full.recv().await);
}