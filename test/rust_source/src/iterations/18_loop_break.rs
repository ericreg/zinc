fn main() {
    let mut i = 0;
    loop {
        println!("{}", i);
        i = (i + 1);
        if (i == 3) {
            break;
        }
    }
    println!("{}", i);
}