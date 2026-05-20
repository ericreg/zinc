use std::collections::{BTreeMap};

fn main() {
    let mut scores = BTreeMap::<String, i64>::new();
    scores.insert(String::from("a"), 1);
    for (key, value) in scores.iter().map(|(k, v)| (k.clone(), v.clone())) {
        let key = "changed";
        let value = (value + 10);
        println!("{}", key);
        println!("{}", value);
    }
    let original = scores.get("a").unwrap().clone();
    println!("{}", original);
}