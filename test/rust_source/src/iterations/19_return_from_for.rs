fn find_i64_i64(limit: i64, target: i64) -> i64 {
    for n in 0..limit {
        if (n == target) {
            return n;
        }
    }
    return (-1);
}

fn find_zero_i64(limit: i64) -> i64 {
    for n in 0..limit {
        return n;
    }
    return (-1);
}

fn main() {
    let found = find_i64_i64(5, 3);
    let missing = find_i64_i64(5, 9);
    let zero = find_zero_i64(0);
    println!("{}", found);
    println!("{}", missing);
    println!("{}", zero);
}