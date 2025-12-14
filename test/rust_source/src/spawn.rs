async fn greet_i64(x: i64) {
    println!("{}", x);
}

#[tokio::main]
async fn main() {
    tokio::spawn(greet_i64(42));
    println!("done");
}