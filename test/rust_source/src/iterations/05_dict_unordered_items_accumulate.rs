use std::collections::{HashMap};

fn main() {
    let mut scores = HashMap::<String, i64>::new();
    scores.insert(String::from("a"), 1);
    scores.insert(String::from("b"), 2);
    let mut total = 0;
    let mut seen = 0;
    for (key, value) in scores.iter().map(|(k, v)| (k.clone(), v.clone())) {
        total = (total + value);
        seen = (seen + 1);
    }
    println!("{}", total);
    println!("{}", seen);
}