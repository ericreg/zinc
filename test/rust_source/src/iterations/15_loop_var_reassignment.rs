fn main() {
    let mut total = 0;
    for x in 0..3 {
        let x = (x + 10);
        total = (total + x);
    }
    println!("{}", total);
}