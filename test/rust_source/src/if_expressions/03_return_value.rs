fn if_expressions_03_return_value__label_i64(count: i64) -> String {
    return if (count == 1) {
        String::from("item")
    } else {
        String::from("items")
    };
}

fn main() {
    println!("{}", if_expressions_03_return_value__label_i64(1));
    println!("{}", if_expressions_03_return_value__label_i64(2));
}