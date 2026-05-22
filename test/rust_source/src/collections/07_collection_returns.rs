use std::collections::{HashMap, HashSet};

fn collections_07_collection_returns__make_scores_i64(seed: i64) -> HashMap<String, f64> {
    return HashMap::from([(String::from("made"), (seed as f64)), (String::from("bonus"), 1.5)]);
}

fn collections_07_collection_returns__make_values_i64(seed: i64) -> HashSet<i64> {
    return HashSet::from([seed, 4]);
}

fn main() {
    let scores = collections_07_collection_returns__make_scores_i64(2);
    let bonus = scores.get("bonus").unwrap().clone();
    println!("{}", bonus);
    let values = collections_07_collection_returns__make_values_i64(5);
    let has_four = values.contains(&4);
    println!("{}", has_four);
}