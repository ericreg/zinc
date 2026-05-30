fn monomorphization_12_multiple_return_statements__classify_i64(n: i64) -> i64 {
    if (n < 0) {
        return (-1);
    }
    if (n == 0) {
        return 0;
    }
    if (n < 10) {
        return 1;
    }
    if (n < 100) {
        return 2;
    }
    return 3;
}

fn main() {
    let a = monomorphization_12_multiple_return_statements__classify_i64((-5));
    println!("classify(-5): {}", a);
    let b = monomorphization_12_multiple_return_statements__classify_i64(0);
    println!("classify(0): {}", b);
    let c = monomorphization_12_multiple_return_statements__classify_i64(5);
    println!("classify(5): {}", c);
    let d = monomorphization_12_multiple_return_statements__classify_i64(50);
    println!("classify(50): {}", d);
    let e = monomorphization_12_multiple_return_statements__classify_i64(100);
    println!("classify(100): {}", e);
    let f = monomorphization_12_multiple_return_statements__classify_i64(999);
    println!("classify(999): {}", f);
}