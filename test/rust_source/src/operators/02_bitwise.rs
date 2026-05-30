fn main() {
    let a: u8 = 0b1010;
    let b: u8 = 0b1100;
    let anded = (a & b);
    let ored = (a | b);
    let xored = (a ^ b);
    let inverted = (!a);
    let shifted_left = (a << 1);
    let shifted_right = (b >> 2);
    let precedence = ((1 << 2) | 1);
    let mut c: u8 = 0b1111;
    c &= (0b1010 as u8);
    c |= (0b0101 as u8);
    c ^= (0b0011 as u8);
    c <<= 1;
    c >>= 2;
    println!("and: {}", anded);
    println!("or: {}", ored);
    println!("xor: {}", xored);
    println!("not: {}", inverted);
    println!("left: {}", shifted_left);
    println!("right: {}", shifted_right);
    println!("precedence: {}", precedence);
    println!("compound: {}", c);
}