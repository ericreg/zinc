fn f_String(x: String) -> String {
    return x;
}

fn f_bool(x: bool) -> bool {
    return x;
}

fn f_f64(x: f64) -> f64 {
    return x;
}

fn f_i64(x: i64) -> i64 {
    return x;
}

fn g_String(x: String) -> String {
    return f_String(x);
}

fn g_bool(x: bool) -> bool {
    return f_bool(x);
}

fn g_f64(x: f64) -> f64 {
    return f_f64(x);
}

fn g_i64(x: i64) -> i64 {
    return f_i64(x);
}

fn h_String(x: String) -> String {
    return g_String(x);
}

fn h_bool(x: bool) -> bool {
    return g_bool(x);
}

fn h_f64(x: f64) -> f64 {
    return g_f64(x);
}

fn h_i64(x: i64) -> i64 {
    return g_i64(x);
}

fn main() {
    let a1 = h_i64(1);
    println!("h(1): {}", a1);
    let a2 = h_f64(1.0);
    println!("h(1.0): {}", a2);
    let a3 = h_bool(true);
    println!("h(true): {}", a3);
    let a4 = h_String(String::from("s"));
    println!("h(s): {}", a4);
    let b1 = g_i64(42);
    let b2 = g_f64(3.14);
    println!("g(42): {}, g(3.14): {}", b1, b2);
    let c1 = f_i64(99);
    let c2 = f_f64(0.5);
    let c3 = f_bool(false);
    let c4 = f_String(String::from("direct"));
    println!("f(99): {}, f(0.5): {}", c1, c2);
    println!("f(false): {}, f(direct): {}", c3, c4);
}