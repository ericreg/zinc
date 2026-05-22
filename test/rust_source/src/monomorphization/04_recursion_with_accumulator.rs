fn monomorphization_04_recursion_with_accumulator__sum_with_acc_i64_f64(n: i64, acc: f64) -> f64 {
    if (n <= 0) {
        return acc;
    }
    return monomorphization_04_recursion_with_accumulator__sum_with_acc_i64_f64((n - 1), (acc + (n as f64)));
}

fn monomorphization_04_recursion_with_accumulator__sum_with_acc_i64_i64(n: i64, acc: i64) -> i64 {
    if (n <= 0) {
        return acc;
    }
    return monomorphization_04_recursion_with_accumulator__sum_with_acc_i64_i64((n - 1), (acc + n));
}

fn main() {
    let x = monomorphization_04_recursion_with_accumulator__sum_with_acc_i64_i64(10, 0);
    println!("sum_with_acc(10, 0): {}", x);
    let y = monomorphization_04_recursion_with_accumulator__sum_with_acc_i64_f64(5, 0.0);
    println!("sum_with_acc(5, 0.0): {}", y);
    let z = monomorphization_04_recursion_with_accumulator__sum_with_acc_i64_i64(3, 100);
    println!("sum_with_acc(3, 100): {}", z);
}