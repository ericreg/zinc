fn main() {
    let a = [1, 2, 3];
    for x in &a {
        println!("{}", x);
    }
    let mut b: Vec<i64> = Vec::new();
    b.push(10);
    b.push(20);
    b.push(30);
    for y in &b {
        println!("{}", y);
    }
}
