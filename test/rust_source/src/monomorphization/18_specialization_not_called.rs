fn monomorphization_18_specialization_not_called__maybe_String(x: String) -> String {
    return x;
}

fn monomorphization_18_specialization_not_called__maybe_i64(x: i64) -> i64 {
    return x;
}

fn main() {
    let a = monomorphization_18_specialization_not_called__maybe_i64(1);
    println!("first call: {}", a);
    let mut temp = 100;
    temp = (temp + 1);
    println!("temp: {}", temp);
    let b = monomorphization_18_specialization_not_called__maybe_i64(2);
    println!("second call: {}", b);
    let c = monomorphization_18_specialization_not_called__maybe_i64(3);
    println!("third call: {}", c);
    println!("more calls:");
    let d = monomorphization_18_specialization_not_called__maybe_i64(4);
    let e = monomorphization_18_specialization_not_called__maybe_i64(5);
    let f = monomorphization_18_specialization_not_called__maybe_i64(6);
    println!("d={}, e={}, f={}", d, e, f);
    let g = monomorphization_18_specialization_not_called__maybe_String(String::from("string"));
    println!("string call: {}", g);
    let h = monomorphization_18_specialization_not_called__maybe_i64(100);
    println!("back to int: {}", h);
}