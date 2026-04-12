fn count_down_int_i64(n: i64) -> f64 {
    println!("int: {}", n);
    if (n <= 0) {
        return (0 as f64);
    }
    return count_down_float_i64((n - 1));
}

fn count_down_float_i64(n: i64) -> f64 {
    println!("float: {}", n);
    if (n <= 0) {
        return 0.0;
    }
    return count_down_int_i64((n - 1));
}

fn main() {
    let result = count_down_int_i64(4);
    println!("result: {}", result);
}