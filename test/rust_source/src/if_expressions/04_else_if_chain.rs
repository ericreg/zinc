fn main() {
    let score = 85;
    let grade = if (score >= 90) {
        String::from("A")
    } else if (score >= 80) {
        String::from("B")
    } else if (score >= 70) {
        String::from("C")
    } else {
        String::from("F")
    };
    println!("{}", grade);
}