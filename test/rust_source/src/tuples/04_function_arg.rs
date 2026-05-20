fn sum_pair_Tuple_i64_i64(pair: (i64, i64)) -> i64 {
    return (pair.0 + pair.1);
}

fn main() {
    let pair = (10, 20);
    let total = sum_pair_Tuple_i64_i64(pair);
    println!("{}", total);
}