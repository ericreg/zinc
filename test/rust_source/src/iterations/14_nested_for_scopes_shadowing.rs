fn main() {
    let x = 99;
    let mut total = 0;
    for x in 0..3 {
        for y in 0..2 {
            total = (total + ((x * y)));
        }
    }
    println!("{}", total);
    println!("{}", x);
}