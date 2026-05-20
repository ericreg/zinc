use std::collections::{BTreeMap};

fn main() {
    let mut scores = BTreeMap::<String, i64>::new();
    scores.insert(String::from("b"), 2);
    scores.insert(String::from("a"), 1);
    let mut collected_keys = vec![];
    for item in scores.iter().map(|(k, v)| (k.clone(), v.clone())) {
        let item_key = item.0;
        let item_value = item.1;
        println!("{}", item_key);
        println!("{}", item_value);
        collected_keys.push(item_key);
    }
    println!("{}", collected_keys[0]);
    println!("{}", collected_keys[1]);
    let collected_count = (collected_keys.len() as i64);
    println!("{}", collected_count);
}