fn monomorphization_05_mutual_three_functions__pang_i64(n: i64) -> i64 {
    println!("pang: {}", n);
    if (n <= 0) {
        return 0;
    }
    return monomorphization_05_mutual_three_functions__ping_i64((n - 1));
}

fn monomorphization_05_mutual_three_functions__pong_i64(n: i64) -> i64 {
    println!("pong: {}", n);
    return monomorphization_05_mutual_three_functions__pang_i64(n);
}

fn monomorphization_05_mutual_three_functions__ping_i64(n: i64) -> i64 {
    println!("ping: {}", n);
    if (n <= 0) {
        return 0;
    }
    return monomorphization_05_mutual_three_functions__pong_i64((n - 1));
}

fn main() {
    let result = monomorphization_05_mutual_three_functions__ping_i64(5);
    println!("final result: {}", result);
}