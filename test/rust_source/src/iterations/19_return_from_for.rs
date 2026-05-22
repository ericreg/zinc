fn iterations_19_return_from_for__find_i64_i64(limit: i64, target: i64) -> i64 {
    for n in 0..limit {
        if (n == target) {
            return n;
        }
    }
    return (-1);
}

fn iterations_19_return_from_for__find_zero_i64(limit: i64) -> i64 {
    for n in 0..limit {
        return n;
    }
    return (-1);
}

fn main() {
    let found = iterations_19_return_from_for__find_i64_i64(5, 3);
    let missing = iterations_19_return_from_for__find_i64_i64(5, 9);
    let zero = iterations_19_return_from_for__find_zero_i64(0);
    println!("{}", found);
    println!("{}", missing);
    println!("{}", zero);
}