fn fib_i64(n: i64) -> i64 {
    if (n <= 1) {
        return n;
    }
    return (fib_i64((n - 1)) + fib_i64((n - 2)));
}

fn main() {
    let result = fib_i64(10);
    println!("fib(10): {}", result);
    let f0 = fib_i64(0);
    println!("fib(0): {}", f0);
    let f1 = fib_i64(1);
    println!("fib(1): {}", f1);
    let f5 = fib_i64(5);
    println!("fib(5): {}", f5);
}