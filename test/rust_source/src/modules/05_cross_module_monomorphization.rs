fn modules__lib_generic__first_String_String(x: String, y: String) -> String {
    return x;
}

fn modules__lib_generic__first_i64_i64(x: i64, y: i64) -> i64 {
    return x;
}

fn main() {
    let a = modules__lib_generic__first_i64_i64(1, 2);
    let b = modules__lib_generic__first_String_String(String::from("a"), String::from("b"));
    println!("{}", a);
    println!("{}", b);
}