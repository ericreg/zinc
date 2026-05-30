fn monomorphization_06_mutual_with_type_promotion__odd_sum_i64_f64(n: i64, acc: f64) -> f64 {
    if (n <= 0) {
        return acc;
    }
    return monomorphization_06_mutual_with_type_promotion__even_sum_i64_f64((n - 1), acc);
}

fn monomorphization_06_mutual_with_type_promotion__even_sum_i64_f64(n: i64, acc: f64) -> f64 {
    if (n <= 0) {
        return acc;
    }
    return monomorphization_06_mutual_with_type_promotion__odd_sum_i64_f64((n - 1), (acc + (n as f64)));
}

fn monomorphization_06_mutual_with_type_promotion__odd_sum_i64_i64(n: i64, acc: i64) -> i64 {
    if (n <= 0) {
        return acc;
    }
    return monomorphization_06_mutual_with_type_promotion__even_sum_i64_i64((n - 1), acc);
}

fn monomorphization_06_mutual_with_type_promotion__even_sum_i64_i64(n: i64, acc: i64) -> i64 {
    if (n <= 0) {
        return acc;
    }
    return monomorphization_06_mutual_with_type_promotion__odd_sum_i64_i64((n - 1), (acc + n));
}

fn main() {
    let x = monomorphization_06_mutual_with_type_promotion__even_sum_i64_i64(10, 0);
    println!("even_sum(10, 0): {}", x);
    let y = monomorphization_06_mutual_with_type_promotion__even_sum_i64_f64(10, 0.0);
    println!("even_sum(10, 0.0): {}", y);
    let z = monomorphization_06_mutual_with_type_promotion__odd_sum_i64_i64(5, 0);
    println!("odd_sum(5, 0): {}", z);
}