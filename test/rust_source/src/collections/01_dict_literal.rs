use std::collections::{HashMap};

fn main() {
    let scores = HashMap::from([(String::from("a"), (1 as f64)), (String::from("b"), 2.5)]);
    let first = scores.get("a").unwrap().clone();
    let second = scores.get("b").unwrap().clone();
    let count = (scores.len() as i64);
    println!("{}", first);
    println!("{}", second);
    println!("{}", count);
}