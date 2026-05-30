use std::collections::{BTreeMap, BTreeSet};

fn main() {
    let mut scores = BTreeMap::<String, i64>::new();
    scores.insert(String::from("x"), 4);
    let x = scores.get("x").unwrap().clone();
    println!("{}", x);
    let mut values = BTreeSet::<i64>::new();
    { values.insert(3); () };
    let has_three = values.contains(&3);
    println!("{}", has_three);
}