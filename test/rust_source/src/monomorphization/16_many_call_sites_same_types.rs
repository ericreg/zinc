fn monomorphization_16_many_call_sites_same_types__inc_i64(x: i64) -> i64 {
    return (x + 1);
}

fn main() {
    let a = monomorphization_16_many_call_sites_same_types__inc_i64(1);
    let b = monomorphization_16_many_call_sites_same_types__inc_i64(2);
    let c = monomorphization_16_many_call_sites_same_types__inc_i64(3);
    let d = monomorphization_16_many_call_sites_same_types__inc_i64(4);
    let e = monomorphization_16_many_call_sites_same_types__inc_i64(5);
    let f = monomorphization_16_many_call_sites_same_types__inc_i64(6);
    let g = monomorphization_16_many_call_sites_same_types__inc_i64(7);
    let h = monomorphization_16_many_call_sites_same_types__inc_i64(8);
    let i = monomorphization_16_many_call_sites_same_types__inc_i64(9);
    let j = monomorphization_16_many_call_sites_same_types__inc_i64(10);
    let sum = (((((((((a + b) + c) + d) + e) + f) + g) + h) + i) + j);
    println!("sum of inc(1) to inc(10): {}", sum);
    let k = monomorphization_16_many_call_sites_same_types__inc_i64(100);
    let l = monomorphization_16_many_call_sites_same_types__inc_i64(200);
    let m = monomorphization_16_many_call_sites_same_types__inc_i64(300);
    println!("k={}, l={}, m={}", k, l, m);
    let n = monomorphization_16_many_call_sites_same_types__inc_i64(monomorphization_16_many_call_sites_same_types__inc_i64(monomorphization_16_many_call_sites_same_types__inc_i64(0)));
    println!("inc(inc(inc(0))): {}", n);
}