fn func_c_i64(n: i64) -> i64 {
    println!("c: {}", n);
    return func_a_i64((n - 1));
}

fn func_b_i64(n: i64) -> i64 {
    println!("b: {}", n);
    return func_c_i64(n);
}

fn func_a_i64(n: i64) -> i64 {
    if (n <= 0) {
        return n;
    }
    println!("a: {}", n);
    return func_b_i64((n - 1));
}

fn main() {
    let result = func_a_i64(5);
    println!("result: {}", result);
}