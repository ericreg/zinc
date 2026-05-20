use std::collections::{BTreeMap};

fn main() {
    let mut scores = BTreeMap::<String, i64>::new();
    scores.insert(String::from("b"), 2);
    scores.insert(String::from("a"), 1);
    for (key, value) in scores.iter().map(|(k, v)| (k.clone(), v.clone())) {
        println!("{}", key);
        println!("{}", value);
    }
}