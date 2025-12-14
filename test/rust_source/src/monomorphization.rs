fn add_f64_f64(a: f64, b: f64) -> f64 {
    return (a + b);
}

fn add_i64_i64(a: i64, b: i64) -> i64 {
    return (a + b);
}

fn main() {
    let x = add_i64_i64(1, 2);
    let y = add_f64_f64(1.0, 2.0);
    println!("{}", x);
    println!("{}", y);
}
