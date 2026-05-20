use std::collections::{HashMap};

fn main() {
    let mut scores = HashMap::<String, i64>::new();
    scores.insert(String::from("a"), 1);
    scores.insert(String::from("b"), 2);
    let mut key_count = 0;
    for key in scores.keys().cloned() {
        key_count = (key_count + 1);
    }
    let mut value_total = 0;
    for value in scores.values().cloned() {
        value_total = (value_total + value);
    }
    let mut item_total = 0;
    let mut item_count = 0;
    for (key, value) in scores.iter().map(|(k, v)| (k.clone(), v.clone())) {
        item_total = (item_total + value);
        item_count = (item_count + 1);
    }
    println!("{}", key_count);
    println!("{}", value_total);
    println!("{}", item_total);
    println!("{}", item_count);
}