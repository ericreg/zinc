fn main() {
    let x = 10;
    if x > 5 {
        println!("x is greater than 5");
    }
    if x > 15 {
        println!("x is greater than 15");
    } else {
        println!("x is not greater than 15");
    }
    if x > 20 {
        println!("big");
    } else if x > 5 {
        println!("medium");
    } else {
        println!("small");
    }
}
