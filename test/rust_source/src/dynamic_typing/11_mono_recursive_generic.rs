fn dynamic_typing_11_mono_recursive_generic__countdown_i64(n: i64) -> i64 {
    if (n <= 0) {
        println!("done");
        return 0;
    }
    println!("n: {}", n);
    return dynamic_typing_11_mono_recursive_generic__countdown_i64((n - 1));
}

fn dynamic_typing_11_mono_recursive_generic__factorial_i64(n: i64) -> i64 {
    if (n <= 1) {
        return 1;
    }
    return (n * dynamic_typing_11_mono_recursive_generic__factorial_i64((n - 1)));
}

fn dynamic_typing_11_mono_recursive_generic__sum_to_i64(n: i64) -> i64 {
    if (n <= 0) {
        return 0;
    }
    return (n + dynamic_typing_11_mono_recursive_generic__sum_to_i64((n - 1)));
}

fn main() {
    let result1 = dynamic_typing_11_mono_recursive_generic__countdown_i64(5);
    println!("countdown result: {}", result1);
    let result2 = dynamic_typing_11_mono_recursive_generic__sum_to_i64(10);
    println!("sum_to(10): {}", result2);
    let result3 = dynamic_typing_11_mono_recursive_generic__factorial_i64(5);
    println!("factorial(5): {}", result3);
    let result5 = dynamic_typing_11_mono_recursive_generic__sum_to_i64(5);
    println!("sum_to(5): {}", result5);
}