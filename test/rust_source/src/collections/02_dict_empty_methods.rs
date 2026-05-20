use std::collections::{HashMap};

fn main() {
    let mut scores = HashMap::<String, i64>::new();
    scores.insert(String::from("left"), 10);
    scores.insert(String::from("right"), 20);
    let right = scores.get("right").unwrap().clone();
    let has_left = scores.contains_key("left");
    println!("{}", right);
    println!("{}", has_left);
    scores.remove("left");
    let after_remove = (scores.len() as i64);
    println!("{}", after_remove);
    scores.clear();
    let is_empty = scores.is_empty();
    println!("{}", is_empty);
}