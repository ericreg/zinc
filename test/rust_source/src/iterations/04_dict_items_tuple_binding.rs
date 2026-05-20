use std::collections::{BTreeMap};

fn main() {
    let mut scores = BTreeMap::<String, i64>::new();
    scores.insert(String::from("b"), 2);
    scores.insert(String::from("a"), 1);
    for item in scores.iter().map(|(k, v)| (k.clone(), v.clone())) {
        let key = item.0;
        let value = item.1;
        println!("{}", key);
        println!("{}", value);
    }
}