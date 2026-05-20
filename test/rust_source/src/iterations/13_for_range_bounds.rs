fn main() {
    for value in 0..3 {
        println!("{}", value);
    }
    for value in 1..=3 {
        println!("{}", value);
    }
    let mut empty_count = 0;
    for value in 0..0 {
        empty_count = (empty_count + 1);
    }
    println!("{}", empty_count);
    let mut count = 0;
    let mut last = (-1);
    for value in 0..300 {
        count = (count + 1);
        last = value;
    }
    println!("{}", count);
    println!("{}", last);
}