use std::collections::{BTreeMap};

fn main() {
    let mut scores = BTreeMap::<String, i64>::new();
    scores.insert(String::from("b"), 2);
    scores.insert(String::from("a"), 1);
    for key in scores.keys().cloned() {
        println!("{}", key);
    }
    for value in scores.values().cloned() {
        println!("{}", value);
    }
}