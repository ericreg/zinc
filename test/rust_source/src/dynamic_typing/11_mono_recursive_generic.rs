fn countdown_i64(n: i64) -> i64 {
    if (n <= 0) {
        println!("done");
        return 0;
    }
    println!("n: {}", n);
    return countdown_i64((n - 1));
}

fn factorial_i64(n: i64) -> i64 {
    if (n <= 1) {
        return 1;
    }
    return (n * factorial_i64((n - 1)));
}

fn sum_to_i64(n: i64) -> i64 {
    if (n <= 0) {
        return 0;
    }
    return (n + sum_to_i64((n - 1)));
}

fn main() {
    let result1 = countdown_i64(5);
    println!("countdown result: {}", result1);
    let result2 = sum_to_i64(10);
    println!("sum_to(10): {}", result2);
    let result3 = factorial_i64(5);
    println!("factorial(5): {}", result3);
    let result5 = sum_to_i64(5);
    println!("sum_to(5): {}", result5);
}