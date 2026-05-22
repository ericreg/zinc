fn monomorphization_08_same_call_different_contexts__double_i64(x: i64) -> i64 {
    return (x + x);
}

fn main() {
    let a = monomorphization_08_same_call_different_contexts__double_i64(5);
    println!("before loop: {}", a);
    let mut i = 0;
    while (i < 3) {
        let b = monomorphization_08_same_call_different_contexts__double_i64(i);
        println!("in loop {}: {}", i, b);
        i = (i + 1);
    }
    let c = monomorphization_08_same_call_different_contexts__double_i64(100);
    println!("after loop: {}", c);
    if true {
        let d = monomorphization_08_same_call_different_contexts__double_i64(42);
        println!("in if: {}", d);
    }
    println!("a={}, c={}", a, c);
}