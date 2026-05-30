use std::collections::{BTreeMap};

fn main() {
    let mut scores = BTreeMap::<String, i64>::new();
    scores.insert(String::from("b"), 2);
    scores.insert(String::from("a"), 1);
    let key = "outer";
    let value = 99;
    let mut collected_keys = vec![];
    for (key, value) in scores.iter().map(|(k, v)| (k.clone(), v.clone())) {
        println!("{}", key);
        println!("{}", value);
        collected_keys.push(key);
    }
    for (key, value) in scores.iter().map(|(k, v)| (k.clone(), v.clone())) {
        println!("{}", key);
        println!("{}", value);
    }
    println!("{}", key);
    println!("{}", value);
    println!("{}", collected_keys[0]);
    println!("{}", collected_keys[1]);
    let collected_count = (collected_keys.len() as i64);
    let score_count = (scores.len() as i64);
    let first_score = scores.get("a").unwrap().clone();
    println!("{}", collected_count);
    println!("{}", score_count);
    println!("{}", first_score);
}