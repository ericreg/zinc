fn if_expressions_06_both_branches_diverge__choose_bool(flag: bool) -> String {
    let ignored = if flag {
        return String::from("left");
    } else {
        return String::from("right");
    };
}

fn main() {
    println!("{}", if_expressions_06_both_branches_diverge__choose_bool(true));
    println!("{}", if_expressions_06_both_branches_diverge__choose_bool(false));
}