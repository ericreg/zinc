fn main() {
    let mut x = 10;
    x += 5;
    x -= 3;
    x *= 2;
    x /= 4;
    x %= 4;
    println!("x: {}", x);
    let y = (2 as i64).pow(((3 as i64).pow((2) as u32)) as u32);
    let z = (((2 as i64).pow((3) as u32)) as i64).pow((2) as u32);
    println!("y: {}, z: {}", y, z);
    let mut f: f64 = 2.0;
    f = (f).powf((3 as f64));
    f += (2 as f64);
    f /= (2 as f64);
    println!("f: {}", f);
}