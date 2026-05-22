fn monomorphization_14_return_function_call__add_f64_f64(a: f64, b: f64) -> f64 {
    return (a + b);
}

fn monomorphization_14_return_function_call__add_i64_f64(a: i64, b: f64) -> f64 {
    return ((a as f64) + b);
}

fn monomorphization_14_return_function_call__add_i64_i64(a: i64, b: i64) -> i64 {
    return (a + b);
}

fn monomorphization_14_return_function_call__double_via_add_f64(x: f64) -> f64 {
    return monomorphization_14_return_function_call__add_f64_f64(x, x);
}

fn monomorphization_14_return_function_call__double_via_add_i64(x: i64) -> i64 {
    return monomorphization_14_return_function_call__add_i64_i64(x, x);
}

fn monomorphization_14_return_function_call__wrapper_f64_f64(x: f64, y: f64) -> f64 {
    return monomorphization_14_return_function_call__add_f64_f64(x, y);
}

fn monomorphization_14_return_function_call__wrapper_i64_f64(x: i64, y: f64) -> f64 {
    return monomorphization_14_return_function_call__add_i64_f64(x, y);
}

fn monomorphization_14_return_function_call__wrapper_i64_i64(x: i64, y: i64) -> i64 {
    return monomorphization_14_return_function_call__add_i64_i64(x, y);
}

fn main() {
    let a = monomorphization_14_return_function_call__wrapper_i64_i64(1, 2);
    println!("wrapper(1, 2): {}", a);
    let b = monomorphization_14_return_function_call__wrapper_f64_f64(1.0, 2.0);
    println!("wrapper(1.0, 2.0): {}", b);
    let c = monomorphization_14_return_function_call__wrapper_i64_f64(1, 2.0);
    println!("wrapper(1, 2.0): {}", c);
    let d = monomorphization_14_return_function_call__double_via_add_i64(5);
    println!("double_via_add(5): {}", d);
    let e = monomorphization_14_return_function_call__double_via_add_f64(2.5);
    println!("double_via_add(2.5): {}", e);
    let f = ((monomorphization_14_return_function_call__wrapper_i64_i64(10, 20) as f64) + 0.5);
    println!("wrapper(10, 20) + 0.5: {}", f);
}