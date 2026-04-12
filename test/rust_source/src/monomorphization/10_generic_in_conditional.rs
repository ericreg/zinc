fn identity_String(x: String) -> String {
    return x;
}

fn identity_bool(x: bool) -> bool {
    return x;
}

fn identity_f64(x: f64) -> f64 {
    return x;
}

fn identity_i64(x: i64) -> i64 {
    return x;
}

fn main() {
    let cond = true;
    if cond {
        let a = identity_i64(42);
        println!("int branch: {}", a);
    } else {
        let b = identity_f64(3.14);
        println!("float branch: {}", b);
    }
    let c = identity_String(String::from("hello"));
    println!("string: {}", c);
    let d = identity_bool(false);
    println!("bool: {}", d);
    if (!cond) {
        let e = identity_i64(999);
        println!("never reached: {}", e);
    }
    println!("test complete");
}