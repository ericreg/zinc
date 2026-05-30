fn main() {
    let t = true;
    let f = false;
    println!("t: {}", t);
    println!("f: {}", f);
    let and_result = (t && f);
    println!("t && f: {}", and_result);
    let or_result = (t || f);
    println!("t || f: {}", or_result);
    let not_result = (!t);
    println!("!t: {}", not_result);
    let n = (1 + 1);
    println!("1 + 1: {}", n);
    let m = (2.0 * 3.0);
    println!("2.0 * 3.0: {}", m);
    println!("test complete");
}