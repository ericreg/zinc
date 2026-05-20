use std::collections::{HashSet};

fn main() {
    let mut values = HashSet::<i64>::new();
    values.insert(1);
    values.insert(2);
    let has_two = values.contains(&2);
    println!("{}", has_two);
    values.clear();
    let is_empty = values.is_empty();
    println!("{}", is_empty);
}