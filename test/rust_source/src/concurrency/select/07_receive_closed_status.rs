use zinc_internal::{Channel};

#[tokio::main]
async fn main() {
    let values = Channel::<i64>::unbounded();
    values.send(7).await;
    values.close();
    let first = values.recv().await;
    println!("{}", first);
    tokio::select! {
        __zinc_select_value_0_0 = async { values.recv_option().await } => {
            let (value, is_open) = match __zinc_select_value_0_0 { Some(value) => (value, true), None => (Default::default(), false) };
            println!("{}", value);
            println!("{}", is_open);
        },
    }
}