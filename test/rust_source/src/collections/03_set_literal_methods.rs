use std::collections::{HashSet};

fn main() {
    let mut values = HashSet::from([1, 2, 3]);
    let has_two = values.contains(&2);
    println!("{}", has_two);
    values.remove(&1);
    let count = (values.len() as i64);
    println!("{}", count);
}