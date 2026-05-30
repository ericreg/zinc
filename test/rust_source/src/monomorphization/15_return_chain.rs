fn monomorphization_15_return_chain__l1_String(x: String) -> String {
    return x;
}

fn monomorphization_15_return_chain__l1_bool(x: bool) -> bool {
    return x;
}

fn monomorphization_15_return_chain__l1_f64(x: f64) -> f64 {
    return x;
}

fn monomorphization_15_return_chain__l1_i64(x: i64) -> i64 {
    return x;
}

fn monomorphization_15_return_chain__l2_String(x: String) -> String {
    return monomorphization_15_return_chain__l1_String(x);
}

fn monomorphization_15_return_chain__l2_bool(x: bool) -> bool {
    return monomorphization_15_return_chain__l1_bool(x);
}

fn monomorphization_15_return_chain__l2_f64(x: f64) -> f64 {
    return monomorphization_15_return_chain__l1_f64(x);
}

fn monomorphization_15_return_chain__l2_i64(x: i64) -> i64 {
    return monomorphization_15_return_chain__l1_i64(x);
}

fn monomorphization_15_return_chain__l3_String(x: String) -> String {
    return monomorphization_15_return_chain__l2_String(x);
}

fn monomorphization_15_return_chain__l3_bool(x: bool) -> bool {
    return monomorphization_15_return_chain__l2_bool(x);
}

fn monomorphization_15_return_chain__l3_f64(x: f64) -> f64 {
    return monomorphization_15_return_chain__l2_f64(x);
}

fn monomorphization_15_return_chain__l3_i64(x: i64) -> i64 {
    return monomorphization_15_return_chain__l2_i64(x);
}

fn monomorphization_15_return_chain__l4_String(x: String) -> String {
    return monomorphization_15_return_chain__l3_String(x);
}

fn monomorphization_15_return_chain__l4_bool(x: bool) -> bool {
    return monomorphization_15_return_chain__l3_bool(x);
}

fn monomorphization_15_return_chain__l4_f64(x: f64) -> f64 {
    return monomorphization_15_return_chain__l3_f64(x);
}

fn monomorphization_15_return_chain__l4_i64(x: i64) -> i64 {
    return monomorphization_15_return_chain__l3_i64(x);
}

fn monomorphization_15_return_chain__l5_String(x: String) -> String {
    return monomorphization_15_return_chain__l4_String(x);
}

fn monomorphization_15_return_chain__l5_bool(x: bool) -> bool {
    return monomorphization_15_return_chain__l4_bool(x);
}

fn monomorphization_15_return_chain__l5_f64(x: f64) -> f64 {
    return monomorphization_15_return_chain__l4_f64(x);
}

fn monomorphization_15_return_chain__l5_i64(x: i64) -> i64 {
    return monomorphization_15_return_chain__l4_i64(x);
}

fn main() {
    let a = monomorphization_15_return_chain__l5_i64(42);
    println!("l5(42): {}", a);
    let b = monomorphization_15_return_chain__l5_f64(3.14);
    println!("l5(3.14): {}", b);
    let c = monomorphization_15_return_chain__l5_String(String::from("chain"));
    println!("l5(chain): {}", c);
    let d = monomorphization_15_return_chain__l5_bool(true);
    println!("l5(true): {}", d);
    let e = monomorphization_15_return_chain__l3_i64(100);
    println!("l3(100): {}", e);
    let f = monomorphization_15_return_chain__l2_f64(0.5);
    println!("l2(0.5): {}", f);
}