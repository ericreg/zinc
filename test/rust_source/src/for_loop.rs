fn main() {
    let a = vec![1, 2, 3];
    for x in a {
        println!("{}", x);
    }
    let mut b = vec![];
    b.push(10);
    b.push(20);
    b.push(30);
    for y in b {
        println!("{}", y);
    }
}