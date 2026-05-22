fn monomorphization_17_combinatorial_explosion__f_String(x: String) -> String {
    return x;
}

fn monomorphization_17_combinatorial_explosion__f_bool(x: bool) -> bool {
    return x;
}

fn monomorphization_17_combinatorial_explosion__f_f64(x: f64) -> f64 {
    return x;
}

fn monomorphization_17_combinatorial_explosion__f_i64(x: i64) -> i64 {
    return x;
}

fn monomorphization_17_combinatorial_explosion__g_String(x: String) -> String {
    return monomorphization_17_combinatorial_explosion__f_String(x);
}

fn monomorphization_17_combinatorial_explosion__g_bool(x: bool) -> bool {
    return monomorphization_17_combinatorial_explosion__f_bool(x);
}

fn monomorphization_17_combinatorial_explosion__g_f64(x: f64) -> f64 {
    return monomorphization_17_combinatorial_explosion__f_f64(x);
}

fn monomorphization_17_combinatorial_explosion__g_i64(x: i64) -> i64 {
    return monomorphization_17_combinatorial_explosion__f_i64(x);
}

fn monomorphization_17_combinatorial_explosion__h_String(x: String) -> String {
    return monomorphization_17_combinatorial_explosion__g_String(x);
}

fn monomorphization_17_combinatorial_explosion__h_bool(x: bool) -> bool {
    return monomorphization_17_combinatorial_explosion__g_bool(x);
}

fn monomorphization_17_combinatorial_explosion__h_f64(x: f64) -> f64 {
    return monomorphization_17_combinatorial_explosion__g_f64(x);
}

fn monomorphization_17_combinatorial_explosion__h_i64(x: i64) -> i64 {
    return monomorphization_17_combinatorial_explosion__g_i64(x);
}

fn main() {
    let a1 = monomorphization_17_combinatorial_explosion__h_i64(1);
    println!("h(1): {}", a1);
    let a2 = monomorphization_17_combinatorial_explosion__h_f64(1.0);
    println!("h(1.0): {}", a2);
    let a3 = monomorphization_17_combinatorial_explosion__h_bool(true);
    println!("h(true): {}", a3);
    let a4 = monomorphization_17_combinatorial_explosion__h_String(String::from("s"));
    println!("h(s): {}", a4);
    let b1 = monomorphization_17_combinatorial_explosion__g_i64(42);
    let b2 = monomorphization_17_combinatorial_explosion__g_f64(3.14);
    println!("g(42): {}, g(3.14): {}", b1, b2);
    let c1 = monomorphization_17_combinatorial_explosion__f_i64(99);
    let c2 = monomorphization_17_combinatorial_explosion__f_f64(0.5);
    let c3 = monomorphization_17_combinatorial_explosion__f_bool(false);
    let c4 = monomorphization_17_combinatorial_explosion__f_String(String::from("direct"));
    println!("f(99): {}, f(0.5): {}", c1, c2);
    println!("f(false): {}, f(direct): {}", c3, c4);
}