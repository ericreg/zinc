use zinc_internal::{__ZincChannel};

#[tokio::main]
async fn main() {
    let primary = __ZincChannel::<i64>::bounded(1);
    let backup = __ZincChannel::<i64>::bounded(1);
    primary.send(1).await;
    tokio::select! {
        __zinc_select_result_0_0 = async { primary.send(2).await } => {
            println!("primary");
        },
        __zinc_select_result_0_1 = async { backup.send(3).await } => {
            println!("backup");
        },
    }
    println!("{}", primary.recv().await);
    println!("{}", backup.recv().await);
}