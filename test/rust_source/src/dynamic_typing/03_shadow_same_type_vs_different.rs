fn main() {
    let mut a = 1;
    a = 2;
    a = 3;
    println!("a (int mutated): {}", a);
    let mut a = "now string";
    println!("a (shadowed to string): {}", a);
    a = "still string";
    a = "another string";
    println!("a (string mutated): {}", a);
    let a = 99.9;
    println!("a (shadowed to float): {}", a);
    let mut b = 1;
    println!("b: {}", b);
    b = 2;
    println!("b: {}", b);
    let mut b = 2.0;
    println!("b: {}", b);
    b = 3.0;
    println!("b: {}", b);
    let mut b = true;
    println!("b: {}", b);
    b = false;
    println!("b: {}", b);
    let b = "end";
    println!("b: {}", b);
}