fn main() {
    let a = (true && true);
    println!("true && true: {}", a);
    let b = (true && false);
    println!("true && false: {}", b);
    let c = (false || true);
    println!("false || true: {}", c);
    let d = (false || false);
    println!("false || false: {}", d);
    let e = (!true);
    println!("!true: {}", e);
    let f = (!false);
    println!("!false: {}", f);
    let g = (true && true);
    println!("true and true: {}", g);
    let h = (false || true);
    println!("false or true: {}", h);
    let i = (!false);
    println!("not false (using !): {}", i);
    let j = (((true && false)) || ((true && true)));
    println!("(true && false) || (true && true): {}", j);
    let k = (!((true && false)));
    println!("!(true && false): {}", k);
    let l = (((1 > 0)) && ((2 > 1)));
    println!("(1 > 0) && (2 > 1): {}", l);
    let m = (((1 < 0)) || ((2 > 1)));
    println!("(1 < 0) || (2 > 1): {}", m);
    println!("test complete");
}