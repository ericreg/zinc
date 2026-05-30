fn main() {
    let nested = (1, (2, 3));
    let inner = nested.1;
    let first = inner.0;
    let second = nested.1.1;
    println!("{}", first);
    println!("{}", second);
}