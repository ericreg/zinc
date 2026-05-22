fn iterations_21_return_from_tuple_for__find_value_Vec_Tuple_i64_i64_i64(pairs: &Vec<(i64, i64)>, target: i64) -> i64 {
    for (index, value) in pairs.iter().cloned() {
        if (index == target) {
            return value;
        }
    }
    return (-1);
}

fn main() {
    let pairs = vec![(1, 10), (2, 20)];
    let found = iterations_21_return_from_tuple_for__find_value_Vec_Tuple_i64_i64_i64(&pairs, 2);
    let missing = iterations_21_return_from_tuple_for__find_value_Vec_Tuple_i64_i64_i64(&pairs, 9);
    println!("{}", found);
    println!("{}", missing);
}