fn dynamic_typing_10_mono_many_specializations__add_f64_f64(a: f64, b: f64) -> f64 {
    return (a + b);
}

fn dynamic_typing_10_mono_many_specializations__add_f64_i64(a: f64, b: i64) -> f64 {
    return (a + (b as f64));
}

fn dynamic_typing_10_mono_many_specializations__add_i64_f64(a: i64, b: f64) -> f64 {
    return ((a as f64) + b);
}

fn dynamic_typing_10_mono_many_specializations__add_i64_i64(a: i64, b: i64) -> i64 {
    return (a + b);
}

fn dynamic_typing_10_mono_many_specializations__identity_String(x: String) -> String {
    return x;
}

fn dynamic_typing_10_mono_many_specializations__identity_bool(x: bool) -> bool {
    return x;
}

fn dynamic_typing_10_mono_many_specializations__identity_f64(x: f64) -> f64 {
    return x;
}

fn dynamic_typing_10_mono_many_specializations__identity_i64(x: i64) -> i64 {
    return x;
}

fn dynamic_typing_10_mono_many_specializations__process_f64_f64_f64(x: f64, y: f64, z: f64) -> f64 {
    return ((x + y) + z);
}

fn dynamic_typing_10_mono_many_specializations__process_i64_f64_i64(x: i64, y: f64, z: i64) -> f64 {
    return (((x as f64) + y) + (z as f64));
}

fn dynamic_typing_10_mono_many_specializations__process_i64_i64_i64(x: i64, y: i64, z: i64) -> i64 {
    return ((x + y) + z);
}

fn main() {
    let a = dynamic_typing_10_mono_many_specializations__identity_i64(1);
    println!("identity(int): {}", a);
    let b = dynamic_typing_10_mono_many_specializations__identity_f64(3.14);
    println!("identity(float): {}", b);
    let c = dynamic_typing_10_mono_many_specializations__identity_bool(true);
    println!("identity(bool): {}", c);
    let d = dynamic_typing_10_mono_many_specializations__identity_String(String::from("hello"));
    println!("identity(string): {}", d);
    let e = dynamic_typing_10_mono_many_specializations__add_i64_i64(1, 2);
    println!("add(int, int): {}", e);
    let f = dynamic_typing_10_mono_many_specializations__add_f64_f64(1.0, 2.0);
    println!("add(float, float): {}", f);
    let g = dynamic_typing_10_mono_many_specializations__add_i64_f64(1, 2.0);
    println!("add(int, float): {}", g);
    let h = dynamic_typing_10_mono_many_specializations__add_f64_i64(1.0, 2);
    println!("add(float, int): {}", h);
    let i = dynamic_typing_10_mono_many_specializations__process_i64_i64_i64(1, 2, 3);
    println!("process(int, int, int): {}", i);
    let j = dynamic_typing_10_mono_many_specializations__process_f64_f64_f64(1.0, 2.0, 3.0);
    println!("process(float, float, float): {}", j);
    let k = dynamic_typing_10_mono_many_specializations__process_i64_f64_i64(1, 2.0, 3);
    println!("process(int, float, int): {}", k);
    let l = dynamic_typing_10_mono_many_specializations__add_i64_f64(10, 0.5);
    println!("add(10, 0.5): {}", l);
}