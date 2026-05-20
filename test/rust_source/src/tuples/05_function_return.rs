fn make_pair_i64(seed: i64) -> (i64, i64) {
    return (seed, (seed + 1));
}

fn main() {
    let (left, right) = make_pair_i64(4);
    println!("{}", left);
    println!("{}", right);
}