const MODULES__LIB_MATH__MAGIC: i64 = 10;

fn modules__lib_math__add_i64_i64(a: i64, b: i64) -> i64 {
    return (a + b);
}

fn main() {
    let total = modules__lib_math__add_i64_i64(2, 3);
    let shifted = (total + MODULES__LIB_MATH__MAGIC);
    println!("total={}", total);
    println!("shifted={}", shifted);
}