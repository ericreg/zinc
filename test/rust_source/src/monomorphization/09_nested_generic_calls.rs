fn inner_f64(x: f64) -> f64 {
    return (x + (1 as f64));
}

fn inner_i64(x: i64) -> i64 {
    return (x + 1);
}

fn middle_i64(x: i64) -> i64 {
    return (inner_i64(x) + inner_i64(x));
}

fn middle_f64(x: f64) -> f64 {
    return (inner_f64(x) + inner_f64(x));
}

fn outer_f64(x: f64) -> f64 {
    return (middle_f64(x) * (2 as f64));
}

fn outer_i64(x: i64) -> i64 {
    return (middle_i64(x) * 2);
}

fn main() {
    let a = outer_i64(5);
    println!("outer(5): {}", a);
    let b = outer_f64(2.5);
    println!("outer(2.5): {}", b);
    let c = inner_i64(10);
    println!("inner(10): {}", c);
    let d = inner_f64(0.5);
    println!("inner(0.5): {}", d);
    let e = middle_i64(3);
    println!("middle(3): {}", e);
}