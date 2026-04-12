fn add_f64_f64(a: f64, b: f64) -> f64 {
    return (a + b);
}

fn add_i64_f64(a: i64, b: f64) -> f64 {
    return ((a as f64) + b);
}

fn add_i64_i64(a: i64, b: i64) -> i64 {
    return (a + b);
}

fn double_via_add_f64(x: f64) -> f64 {
    return add_f64_f64(x, x);
}

fn double_via_add_i64(x: i64) -> i64 {
    return add_i64_i64(x, x);
}

fn wrapper_f64_f64(x: f64, y: f64) -> f64 {
    return add_f64_f64(x, y);
}

fn wrapper_i64_f64(x: i64, y: f64) -> f64 {
    return add_i64_f64(x, y);
}

fn wrapper_i64_i64(x: i64, y: i64) -> i64 {
    return add_i64_i64(x, y);
}

fn main() {
    let a = wrapper_i64_i64(1, 2);
    println!("wrapper(1, 2): {}", a);
    let b = wrapper_f64_f64(1.0, 2.0);
    println!("wrapper(1.0, 2.0): {}", b);
    let c = wrapper_i64_f64(1, 2.0);
    println!("wrapper(1, 2.0): {}", c);
    let d = double_via_add_i64(5);
    println!("double_via_add(5): {}", d);
    let e = double_via_add_f64(2.5);
    println!("double_via_add(2.5): {}", e);
    let f = ((wrapper_i64_i64(10, 20) as f64) + 0.5);
    println!("wrapper(10, 20) + 0.5: {}", f);
}