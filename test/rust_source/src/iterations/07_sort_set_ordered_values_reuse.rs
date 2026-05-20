use std::collections::{BTreeSet};

fn main() {
    let mut values = BTreeSet::<i64>::new();
    values.insert(3);
    values.insert(1);
    values.insert(2);
    let mut total = 0;
    for value in values.iter().cloned() {
        println!("{}", value);
        total = (total + value);
    }
    let count = (values.len() as i64);
    println!("{}", total);
    println!("{}", count);
}