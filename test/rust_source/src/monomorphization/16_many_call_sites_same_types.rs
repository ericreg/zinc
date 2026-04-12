fn inc_i64(x: i64) -> i64 {
    return (x + 1);
}

fn main() {
    let a = inc_i64(1);
    let b = inc_i64(2);
    let c = inc_i64(3);
    let d = inc_i64(4);
    let e = inc_i64(5);
    let f = inc_i64(6);
    let g = inc_i64(7);
    let h = inc_i64(8);
    let i = inc_i64(9);
    let j = inc_i64(10);
    let sum = (((((((((a + b) + c) + d) + e) + f) + g) + h) + i) + j);
    println!("sum of inc(1) to inc(10): {}", sum);
    let k = inc_i64(100);
    let l = inc_i64(200);
    let m = inc_i64(300);
    println!("k={}, l={}, m={}", k, l, m);
    let n = inc_i64(inc_i64(inc_i64(0)));
    println!("inc(inc(inc(0))): {}", n);
}