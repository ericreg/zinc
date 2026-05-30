use std::collections::{HashSet};

fn main() {
    let mut values = HashSet::<i64>::new();
    let result = { values.insert(1); () };
    println!("{}", (values.len() as i64));
}