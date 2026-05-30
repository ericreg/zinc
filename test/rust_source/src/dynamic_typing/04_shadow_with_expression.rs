fn main() {
    let x = 1;
    println!("x (int): {}", x);
    let x = ((x as f64) + 0.5);
    println!("x (now float): {}", x);
    let y = 10;
    println!("y (int): {}", y);
    let mut y = ((y as f64) * 2.0);
    println!("y (float after *2.0): {}", y);
    y = (y + (5 as f64));
    println!("y (float + int = float): {}", y);
    let z = 100;
    println!("z (int): {}", z);
    let z = ((((z + 1)) as f64) * 0.1);
    println!("z (complex expr): {}", z);
    let mut w = 5;
    w = (w + 3);
    w = (w * 2);
    println!("w (int arithmetic): {}", w);
    let w = ((w as f64) / 2.0);
    println!("w (now float): {}", w);
}