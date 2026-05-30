fn main() {
    let single = (5,);
    let paren = (5);
    let only = single.0;
    println!("{}", only);
    println!("{}", paren);
}