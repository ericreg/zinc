fn main() {
    let mut count = 0;
    let mut outer_count = 0;
    for a in 0..3 {
        for b in 0..3 {
            if (b == 1) {
                break;
            }
            count = (count + 1);
        }
        outer_count = (outer_count + 1);
    }
    println!("{}", count);
    println!("{}", outer_count);
}