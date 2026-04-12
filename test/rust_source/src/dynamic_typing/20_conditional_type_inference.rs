fn abs_value_f64(x: f64) -> f64 {
    if (x < (0 as f64)) {
        return (-x);
    }
    return x;
}

fn abs_value_i64(x: i64) -> i64 {
    if (x < 0) {
        return (-x);
    }
    return x;
}

fn max_val_f64_f64(a: f64, b: f64) -> f64 {
    if (a > b) {
        return a;
    }
    return b;
}

fn max_val_i64_i64(a: i64, b: i64) -> i64 {
    if (a > b) {
        return a;
    }
    return b;
}

fn maybe_return_float_bool(flag: bool) -> f64 {
    if flag {
        return 3.14;
    }
    return 0.0;
}

fn maybe_return_int_bool(flag: bool) -> i64 {
    if flag {
        return 42;
    }
    return 0;
}

fn main() {
    let a = maybe_return_int_bool(true);
    println!("maybe_return_int(true): {}", a);
    let b = maybe_return_int_bool(false);
    println!("maybe_return_int(false): {}", b);
    let c = maybe_return_float_bool(true);
    println!("maybe_return_float(true): {}", c);
    let d = maybe_return_float_bool(false);
    println!("maybe_return_float(false): {}", d);
    let e = abs_value_i64((-5));
    println!("abs_value(-5): {}", e);
    let f = abs_value_i64(5);
    println!("abs_value(5): {}", f);
    let g = abs_value_f64((-3.14));
    println!("abs_value(-3.14): {}", g);
    let h = max_val_i64_i64(10, 20);
    println!("max_val(10, 20): {}", h);
    let i = max_val_f64_f64(3.14, 2.71);
    println!("max_val(3.14, 2.71): {}", i);
    let mut x = 0;
    if true {
        x = 42;
    }
    println!("x after if: {}", x);
    let y = 1;
    if false {
        let y = "never executed";
    }
    println!("y unchanged: {}", y);
    let mut z = 0;
    if true {
        if true {
            z = 100;
        }
    }
    println!("z after nested if: {}", z);
    let flag = (5 > 3);
    if flag {
        println!("5 > 3 is true");
    }
    println!("test complete");
}