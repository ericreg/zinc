fn main() {
    let mut i = 0;
    let mut total = 0;
    println!("write, i: {}, total: {}", i, total);
    loop {
        let action = if (i == 0) {
            i = (i + 1);
            println!("write, i: {}", i);
            continue;
        } else if (i == 3) {
            break;
        } else {
            println!("read, i: {}", i);
            i
        };
        println!("write, action: {}", action);
        total = (total + action);
        i = (i + 1);
        println!("write, total: {}, i: {}", total, i);
    }
    println!("read, total: {}, i: {}", total, i);
}