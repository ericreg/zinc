fn monomorphization_11_call_with_expression_result__process_f64(x: f64) -> f64 {
    return (x * (2 as f64));
}

fn monomorphization_11_call_with_expression_result__process_i64(x: i64) -> i64 {
    return (x * 2);
}

fn main() {
    let a = 10;
    let b = 3.5;
    let result1 = monomorphization_11_call_with_expression_result__process_f64(((a as f64) + b));
    println!("process(a + b): {}", result1);
    let result2 = monomorphization_11_call_with_expression_result__process_i64((a * 2));
    println!("process(a * 2): {}", result2);
    let result3 = monomorphization_11_call_with_expression_result__process_f64(((a as f64) + 0.0));
    println!("process(a + 0.0): {}", result3);
    let result4 = monomorphization_11_call_with_expression_result__process_i64((((a + 5)) * 2));
    println!("process((a + 5) * 2): {}", result4);
    let c = 2;
    let result5 = monomorphization_11_call_with_expression_result__process_f64((((a / c) as f64) + 0.5));
    println!("process(a / c + 0.5): {}", result5);
}