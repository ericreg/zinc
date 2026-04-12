fn process_f64(x: f64) -> f64 {
    if (x < 1.0) {
        return x;
    }
    return process_f64((x * 0.5));
}

fn process_i64(x: i64) -> f64 {
    if ((x as f64) < 1.0) {
        return (x as f64);
    }
    return process_f64(((x as f64) * 0.5));
}

fn main() {
    let result1 = process_i64(10);
    println!("process(10): {}", result1);
    let result2 = process_f64(10.0);
    println!("process(10.0): {}", result2);
}