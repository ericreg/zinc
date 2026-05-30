fn monomorphization_09_nested_generic_calls__inner_f64(x: f64) -> f64 {
    return (x + (1 as f64));
}

fn monomorphization_09_nested_generic_calls__inner_i64(x: i64) -> i64 {
    return (x + 1);
}

fn monomorphization_09_nested_generic_calls__middle_i64(x: i64) -> i64 {
    return (monomorphization_09_nested_generic_calls__inner_i64(x) + monomorphization_09_nested_generic_calls__inner_i64(x));
}

fn monomorphization_09_nested_generic_calls__middle_f64(x: f64) -> f64 {
    return (monomorphization_09_nested_generic_calls__inner_f64(x) + monomorphization_09_nested_generic_calls__inner_f64(x));
}

fn monomorphization_09_nested_generic_calls__outer_f64(x: f64) -> f64 {
    return (monomorphization_09_nested_generic_calls__middle_f64(x) * (2 as f64));
}

fn monomorphization_09_nested_generic_calls__outer_i64(x: i64) -> i64 {
    return (monomorphization_09_nested_generic_calls__middle_i64(x) * 2);
}

fn main() {
    let a = monomorphization_09_nested_generic_calls__outer_i64(5);
    println!("outer(5): {}", a);
    let b = monomorphization_09_nested_generic_calls__outer_f64(2.5);
    println!("outer(2.5): {}", b);
    let c = monomorphization_09_nested_generic_calls__inner_i64(10);
    println!("inner(10): {}", c);
    let d = monomorphization_09_nested_generic_calls__inner_f64(0.5);
    println!("inner(0.5): {}", d);
    let e = monomorphization_09_nested_generic_calls__middle_i64(3);
    println!("middle(3): {}", e);
}