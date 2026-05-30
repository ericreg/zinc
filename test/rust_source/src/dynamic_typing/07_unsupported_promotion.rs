fn main() {
    let s = "hello";
    println!("s: {}", s);
    let n = 42;
    println!("n: {}", n);
    let x = (1 + 2);
    println!("x (int + int): {}", x);
    let y = (1.0 + 2.0);
    println!("y (float + float): {}", y);
    let z = ((1 as f64) + 2.0);
    println!("z (int + float): {}", z);
    let msg = "test complete";
    println!("{}", msg);
}