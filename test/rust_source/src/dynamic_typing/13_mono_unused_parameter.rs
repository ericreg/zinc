fn dynamic_typing_13_mono_unused_parameter__constant_String(x: String) -> i64 {
    return 42;
}

fn dynamic_typing_13_mono_unused_parameter__constant_bool(x: bool) -> i64 {
    return 42;
}

fn dynamic_typing_13_mono_unused_parameter__constant_i64(x: i64) -> i64 {
    return 42;
}

fn dynamic_typing_13_mono_unused_parameter__first_String_i64(a: String, b: i64) -> String {
    return a;
}

fn dynamic_typing_13_mono_unused_parameter__first_f64_bool(a: f64, b: bool) -> f64 {
    return a;
}

fn dynamic_typing_13_mono_unused_parameter__first_i64_i64(a: i64, b: i64) -> i64 {
    return a;
}

fn dynamic_typing_13_mono_unused_parameter__ignore_middle_f64_i64_f64(a: f64, b: i64, c: f64) -> f64 {
    return (a + c);
}

fn dynamic_typing_13_mono_unused_parameter__ignore_middle_i64_String_i64(a: i64, b: String, c: i64) -> i64 {
    return (a + c);
}

fn dynamic_typing_13_mono_unused_parameter__second_bool_i64(a: bool, b: i64) -> i64 {
    return b;
}

fn dynamic_typing_13_mono_unused_parameter__second_i64_String(a: i64, b: String) -> String {
    return b;
}

fn main() {
    let a = dynamic_typing_13_mono_unused_parameter__first_i64_i64(1, 2);
    println!("first(1, 2): {}", a);
    let b = dynamic_typing_13_mono_unused_parameter__first_String_i64(String::from("hello"), 999);
    println!("first(hello, 999): {}", b);
    let c = dynamic_typing_13_mono_unused_parameter__first_f64_bool(3.14, true);
    println!("first(3.14, true): {}", c);
    let d = dynamic_typing_13_mono_unused_parameter__second_i64_String(100, String::from("world"));
    println!("second(100, world): {}", d);
    let e = dynamic_typing_13_mono_unused_parameter__second_bool_i64(true, 42);
    println!("second(true, 42): {}", e);
    let f = dynamic_typing_13_mono_unused_parameter__ignore_middle_i64_String_i64(1, String::from("ignored"), 2);
    println!("ignore_middle(1, ignored, 2): {}", f);
    let g = dynamic_typing_13_mono_unused_parameter__ignore_middle_f64_i64_f64(1.0, 999, 2.0);
    println!("ignore_middle(1.0, 999, 2.0): {}", g);
    let h = dynamic_typing_13_mono_unused_parameter__constant_i64(1);
    println!("constant(1): {}", h);
    let i = dynamic_typing_13_mono_unused_parameter__constant_String(String::from("anything"));
    println!("constant(anything): {}", i);
    let j = dynamic_typing_13_mono_unused_parameter__constant_bool(true);
    println!("constant(true): {}", j);
}