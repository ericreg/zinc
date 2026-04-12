fn pang_i64(n: i64) -> i64 {
    println!("pang: {}", n);
    if (n <= 0) {
        return 0;
    }
    return ping_i64((n - 1));
}

fn pong_i64(n: i64) -> i64 {
    println!("pong: {}", n);
    return pang_i64(n);
}

fn ping_i64(n: i64) -> i64 {
    println!("ping: {}", n);
    if (n <= 0) {
        return 0;
    }
    return pong_i64((n - 1));
}

fn main() {
    let result = ping_i64(5);
    println!("final result: {}", result);
}