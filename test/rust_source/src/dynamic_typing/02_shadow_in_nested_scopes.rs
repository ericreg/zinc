fn main() {
    let x = 10;
    println!("outer before: {}", x);
    let flag = true;
    if flag {
        let x = "inside if";
        println!("inside if: {}", x);
    }
    println!("after if: {}", x);
    let y = 20;
    println!("y before: {}", y);
    if false {
        let y = "never executed";
    } else {
        let y = 3.14;
        println!("in else: {}", y);
    }
    println!("after else: {}", y);
    let z = 1;
    if true {
        if false {
            let z = "nested";
        } else {
            let z = 2.5;
            println!("nested else: {}", z);
        }
    }
    println!("after nested: {}", z);
}