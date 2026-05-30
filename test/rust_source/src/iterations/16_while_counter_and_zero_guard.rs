fn main() {
    let mut i = 0;
    let mut total = 0;
    let mut checks = 0;
    while (i < 4) {
        total = (total + i);
        checks = (checks + 1);
        i = (i + 1);
    }
    let j = 0;
    let mut zero_count = 0;
    while (j < 0) {
        zero_count = (zero_count + 1);
    }
    println!("{}", total);
    println!("{}", checks);
    println!("{}", zero_count);
}