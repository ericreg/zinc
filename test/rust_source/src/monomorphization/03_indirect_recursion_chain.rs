fn monomorphization_03_indirect_recursion_chain__func_c_i64(n: i64) -> i64 {
    println!("c: {}", n);
    return monomorphization_03_indirect_recursion_chain__func_a_i64((n - 1));
}

fn monomorphization_03_indirect_recursion_chain__func_b_i64(n: i64) -> i64 {
    println!("b: {}", n);
    return monomorphization_03_indirect_recursion_chain__func_c_i64(n);
}

fn monomorphization_03_indirect_recursion_chain__func_a_i64(n: i64) -> i64 {
    if (n <= 0) {
        return n;
    }
    println!("a: {}", n);
    return monomorphization_03_indirect_recursion_chain__func_b_i64((n - 1));
}

fn main() {
    let result = monomorphization_03_indirect_recursion_chain__func_a_i64(5);
    println!("result: {}", result);
}