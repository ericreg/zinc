fn main() {
    let values = vec![2, 4, 6];
    let mut total = 0;
    for value in values.iter().cloned() {
        println!("{}", value);
        total = (total + value);
    }
    let count = (values.len() as i64);
    println!("{}", total);
    println!("{}", count);
    println!("{}", values[1]);
}