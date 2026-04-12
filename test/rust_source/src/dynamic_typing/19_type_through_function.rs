fn double_f64(x: f64) -> f64 {
    return (x + x);
}

fn double_i64(x: i64) -> i64 {
    return (x + x);
}

fn identity_f64(x: f64) -> f64 {
    return x;
}

fn identity_i64(x: i64) -> i64 {
    return x;
}

fn negate_f64(x: f64) -> f64 {
    return (-x);
}

fn negate_i64(x: i64) -> i64 {
    return (-x);
}

fn main() {
    let a = 10;
    let b = identity_i64(a);
    println!("a: {}, identity(a): {}", a, b);
    let a = "shadowed";
    println!("a (shadowed): {}, b (still int): {}", a, b);
    let c = 3.14;
    let d = identity_f64(c);
    let c = 999;
    println!("c (shadowed to int): {}, d (still float): {}", c, d);
    let e = 5;
    let f = double_i64(e);
    println!("double(5): {}", f);
    let g = 2.5;
    let h = double_f64(g);
    println!("double(2.5): {}", h);
    let i1 = identity_i64(42);
    let i2 = identity_i64(i1);
    let i = identity_i64(i2);
    println!("triple identity(42): {}", i);
    let j = ((identity_i64(10) as f64) + 0.5);
    println!("identity(10) + 0.5: {}", j);
    let k = negate_i64(5);
    println!("negate(5): {}", k);
    let l = negate_f64(3.14);
    println!("negate(3.14): {}", l);
    let m = 100;
    let n = double_i64(m);
    let m = "string now";
    let o = identity_i64(n);
    println!("m: {}, n: {}, o: {}", m, n, o);
}