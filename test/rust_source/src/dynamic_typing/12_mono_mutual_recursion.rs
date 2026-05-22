fn dynamic_typing_12_mono_mutual_recursion__is_odd_i64(n: i64) -> bool {
    if (n == 0) {
        return false;
    }
    return dynamic_typing_12_mono_mutual_recursion__is_even_i64((n - 1));
}

fn dynamic_typing_12_mono_mutual_recursion__is_even_i64(n: i64) -> bool {
    if (n == 0) {
        return true;
    }
    return dynamic_typing_12_mono_mutual_recursion__is_odd_i64((n - 1));
}

fn dynamic_typing_12_mono_mutual_recursion__pong_i64(n: i64) -> i64 {
    println!("pong: {}", n);
    if (n <= 0) {
        return n;
    }
    return dynamic_typing_12_mono_mutual_recursion__ping_i64((n - 1));
}

fn dynamic_typing_12_mono_mutual_recursion__ping_i64(n: i64) -> i64 {
    println!("ping: {}", n);
    if (n <= 0) {
        return n;
    }
    return dynamic_typing_12_mono_mutual_recursion__pong_i64((n - 1));
}

fn main() {
    let a = dynamic_typing_12_mono_mutual_recursion__is_even_i64(4);
    println!("is_even(4): {}", a);
    let b = dynamic_typing_12_mono_mutual_recursion__is_even_i64(5);
    println!("is_even(5): {}", b);
    let c = dynamic_typing_12_mono_mutual_recursion__is_odd_i64(3);
    println!("is_odd(3): {}", c);
    let d = dynamic_typing_12_mono_mutual_recursion__is_odd_i64(4);
    println!("is_odd(4): {}", d);
    let e = dynamic_typing_12_mono_mutual_recursion__ping_i64(3);
    println!("ping(3) result: {}", e);
    let f = dynamic_typing_12_mono_mutual_recursion__pong_i64(2);
    println!("pong(2) result: {}", f);
}