use std::collections::{BTreeSet};

fn main() {
    let mut values = BTreeSet::<i64>::new();
    values.insert(1);
    for value in values.iter().cloned() {
        let value = 99;
        println!("{}", value);
    }
    let has_one = values.contains(&1);
    let has_99 = values.contains(&99);
    println!("{}", has_one);
    println!("{}", has_99);
}