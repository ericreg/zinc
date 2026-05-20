use std::collections::{HashMap, HashSet};

fn add_score_HashMap_String_f64(scores: &mut HashMap<String, f64>) {
    scores.insert(String::from("c"), (3 as f64));
}

fn has_two_HashSet_i64(values: &HashSet<i64>) -> bool {
    return values.contains(&2);
}

fn sum_scores_HashMap_String_f64(scores: &HashMap<String, f64>) -> f64 {
    return (scores.get("a").unwrap().clone() + scores.get("b").unwrap().clone());
}

fn main() {
    let mut scores = HashMap::from([(String::from("a"), (1 as f64)), (String::from("b"), 2.5)]);
    let total = sum_scores_HashMap_String_f64(&scores);
    println!("{}", total);
    add_score_HashMap_String_f64(&mut scores);
    let score_count = (scores.len() as i64);
    println!("{}", score_count);
    let values = HashSet::from([1, 2]);
    let has_value = has_two_HashSet_i64(&values);
    println!("{}", has_value);
}