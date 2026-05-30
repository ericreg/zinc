fn main() {
    let mut i = 0;
    let mut total = 0;
    while (i < 6) {
        i = (i + 1);
        if (i == 2) {
            continue;
        }
        if (i == 5) {
            break;
        }
        println!("{}", i);
        total = (total + i);
    }
    println!("{}", total);
}