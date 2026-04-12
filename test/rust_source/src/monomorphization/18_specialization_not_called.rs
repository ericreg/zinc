fn maybe_String(x: String) -> String {
    return x;
}

fn maybe_i64(x: i64) -> i64 {
    return x;
}

fn main() {
    let a = maybe_i64(1);
    println!("first call: {}", a);
    let mut temp = 100;
    temp = (temp + 1);
    println!("temp: {}", temp);
    let b = maybe_i64(2);
    println!("second call: {}", b);
    let c = maybe_i64(3);
    println!("third call: {}", c);
    println!("more calls:");
    let d = maybe_i64(4);
    let e = maybe_i64(5);
    let f = maybe_i64(6);
    println!("d={}, e={}, f={}", d, e, f);
    let g = maybe_String(String::from("string"));
    println!("string call: {}", g);
    let h = maybe_i64(100);
    println!("back to int: {}", h);
}