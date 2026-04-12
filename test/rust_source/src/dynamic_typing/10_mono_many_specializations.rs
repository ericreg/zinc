fn add_f64_f64(a: f64, b: f64) -> f64 {
    return (a + b);
}

fn add_f64_i64(a: f64, b: i64) -> f64 {
    return (a + (b as f64));
}

fn add_i64_f64(a: i64, b: f64) -> f64 {
    return ((a as f64) + b);
}

fn add_i64_i64(a: i64, b: i64) -> i64 {
    return (a + b);
}

fn identity_String(x: String) -> String {
    return x;
}

fn identity_bool(x: bool) -> bool {
    return x;
}

fn identity_f64(x: f64) -> f64 {
    return x;
}

fn identity_i64(x: i64) -> i64 {
    return x;
}

fn process_f64_f64_f64(x: f64, y: f64, z: f64) -> f64 {
    return ((x + y) + z);
}

fn process_i64_f64_i64(x: i64, y: f64, z: i64) -> f64 {
    return (((x as f64) + y) + (z as f64));
}

fn process_i64_i64_i64(x: i64, y: i64, z: i64) -> i64 {
    return ((x + y) + z);
}

fn main() {
    let a = identity_i64(1);
    println!("identity(int): {}", a);
    let b = identity_f64(3.14);
    println!("identity(float): {}", b);
    let c = identity_bool(true);
    println!("identity(bool): {}", c);
    let d = identity_String(String::from("hello"));
    println!("identity(string): {}", d);
    let e = add_i64_i64(1, 2);
    println!("add(int, int): {}", e);
    let f = add_f64_f64(1.0, 2.0);
    println!("add(float, float): {}", f);
    let g = add_i64_f64(1, 2.0);
    println!("add(int, float): {}", g);
    let h = add_f64_i64(1.0, 2);
    println!("add(float, int): {}", h);
    let i = process_i64_i64_i64(1, 2, 3);
    println!("process(int, int, int): {}", i);
    let j = process_f64_f64_f64(1.0, 2.0, 3.0);
    println!("process(float, float, float): {}", j);
    let k = process_i64_f64_i64(1, 2.0, 3);
    println!("process(int, float, int): {}", k);
    let l = add_i64_f64(10, 0.5);
    println!("add(10, 0.5): {}", l);
}