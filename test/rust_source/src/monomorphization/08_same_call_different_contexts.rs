fn double_i64(x: i64) -> i64 {
    return (x + x);
}

fn main() {
    let a = double_i64(5);
    println!("before loop: {}", a);
    let mut i = 0;
    while (i < 3) {
        let b = double_i64(i);
        println!("in loop {}: {}", i, b);
        i = (i + 1);
    }
    let c = double_i64(100);
    println!("after loop: {}", c);
    if true {
        let d = double_i64(42);
        println!("in if: {}", d);
    }
    println!("a={}, c={}", a, c);
}