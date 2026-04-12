fn l1_String(x: String) -> String {
    return x;
}

fn l1_bool(x: bool) -> bool {
    return x;
}

fn l1_f64(x: f64) -> f64 {
    return x;
}

fn l1_i64(x: i64) -> i64 {
    return x;
}

fn l2_String(x: String) -> String {
    return l1_String(x);
}

fn l2_bool(x: bool) -> bool {
    return l1_bool(x);
}

fn l2_f64(x: f64) -> f64 {
    return l1_f64(x);
}

fn l2_i64(x: i64) -> i64 {
    return l1_i64(x);
}

fn l3_String(x: String) -> String {
    return l2_String(x);
}

fn l3_bool(x: bool) -> bool {
    return l2_bool(x);
}

fn l3_f64(x: f64) -> f64 {
    return l2_f64(x);
}

fn l3_i64(x: i64) -> i64 {
    return l2_i64(x);
}

fn l4_String(x: String) -> String {
    return l3_String(x);
}

fn l4_bool(x: bool) -> bool {
    return l3_bool(x);
}

fn l4_f64(x: f64) -> f64 {
    return l3_f64(x);
}

fn l4_i64(x: i64) -> i64 {
    return l3_i64(x);
}

fn l5_String(x: String) -> String {
    return l4_String(x);
}

fn l5_bool(x: bool) -> bool {
    return l4_bool(x);
}

fn l5_f64(x: f64) -> f64 {
    return l4_f64(x);
}

fn l5_i64(x: i64) -> i64 {
    return l4_i64(x);
}

fn main() {
    let a = l5_i64(42);
    println!("l5(42): {}", a);
    let b = l5_f64(3.14);
    println!("l5(3.14): {}", b);
    let c = l5_String(String::from("chain"));
    println!("l5(chain): {}", c);
    let d = l5_bool(true);
    println!("l5(true): {}", d);
    let e = l3_i64(100);
    println!("l3(100): {}", e);
    let f = l2_f64(0.5);
    println!("l2(0.5): {}", f);
}