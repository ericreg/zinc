use zinc_internal::{Channel};

#[tokio::main]
async fn main() {
    let values = Channel::<i64>::bounded(2);
    values.send(1).await;
    values.send(2).await;
    values.close();
    let (a, ok1) = match values.recv_option().await { Some(value) => (value, true), None => (Default::default(), false), };
    let (b, ok2) = match values.recv_option().await { Some(value) => (value, true), None => (Default::default(), false), };
    let (c, ok3) = match values.recv_option().await { Some(value) => (value, true), None => (Default::default(), false), };
    println!("{}", a);
    println!("{}", ok1);
    println!("{}", b);
    println!("{}", ok2);
    println!("{}", c);
    println!("{}", ok3);
}