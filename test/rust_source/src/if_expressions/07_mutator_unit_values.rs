use std::collections::{HashSet};

fn main() {
    let mut values = HashSet::<i64>::new();
    let inserted = { values.insert(1); () };
    let result = if true {
        { values.insert(2); () }
    } else {
        println!("skip")
    };
    println!("{}", (values.len() as i64));
}