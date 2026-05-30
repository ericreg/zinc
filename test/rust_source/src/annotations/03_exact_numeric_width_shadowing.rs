fn annotations_03_exact_numeric_width_shadowing__keep_f32_f32(x: f32) -> f32 {
    return x;
}

fn annotations_03_exact_numeric_width_shadowing__keep_f64_f64(x: f64) -> f64 {
    return x;
}

fn annotations_03_exact_numeric_width_shadowing__keep_i32_i32(x: i32) -> i32 {
    return x;
}

fn annotations_03_exact_numeric_width_shadowing__keep_i64_i64(x: i64) -> i64 {
    return x;
}

fn main() {
    let total: i32 = 10;
    println!("{}", annotations_03_exact_numeric_width_shadowing__keep_i32_i32(total));
    let total: i64 = 100;
    println!("{}", annotations_03_exact_numeric_width_shadowing__keep_i64_i64(total));
    let ratio: f32 = 1.25;
    println!("{}", annotations_03_exact_numeric_width_shadowing__keep_f32_f32(ratio));
    let ratio: f64 = 2.5;
    println!("{}", annotations_03_exact_numeric_width_shadowing__keep_f64_f64(ratio));
}