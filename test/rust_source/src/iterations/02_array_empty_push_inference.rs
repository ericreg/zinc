fn main() {
    let mut values = vec![];
    values.push(10);
    values.push(20);
    values.push(30);
    let mut total = 0;
    for value in values.iter().cloned() {
        total = (total + value);
    }
    println!("{}", total);
    println!("{}", values[1]);
}