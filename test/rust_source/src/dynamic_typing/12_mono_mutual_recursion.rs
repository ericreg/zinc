fn is_odd_i64(n: i64) -> bool {
    if (n == 0) {
        return false;
    }
    return is_even_i64((n - 1));
}

fn is_even_i64(n: i64) -> bool {
    if (n == 0) {
        return true;
    }
    return is_odd_i64((n - 1));
}

fn pong_i64(n: i64) -> i64 {
    println!("pong: {}", n);
    if (n <= 0) {
        return n;
    }
    return ping_i64((n - 1));
}

fn ping_i64(n: i64) -> i64 {
    println!("ping: {}", n);
    if (n <= 0) {
        return n;
    }
    return pong_i64((n - 1));
}

fn main() {
    let a = is_even_i64(4);
    println!("is_even(4): {}", a);
    let b = is_even_i64(5);
    println!("is_even(5): {}", b);
    let c = is_odd_i64(3);
    println!("is_odd(3): {}", c);
    let d = is_odd_i64(4);
    println!("is_odd(4): {}", d);
    let e = ping_i64(3);
    println!("ping(3) result: {}", e);
    let f = pong_i64(2);
    println!("pong(2) result: {}", f);
}