use std::collections::{HashSet};

fn main() {
    let mut values = HashSet::<i64>::new();
    { values.insert(1); () };
    { values.insert(2); () };
    { values.insert(3); () };
    let mut total = 0;
    let mut seen = 0;
    for value in values.iter().cloned() {
        total = (total + value);
        seen = (seen + 1);
    }
    let count = (values.len() as i64);
    let has_two = values.contains(&2);
    println!("{}", total);
    println!("{}", seen);
    println!("{}", count);
    println!("{}", has_two);
}