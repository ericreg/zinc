fn main() {
    let a = ((((((1 as f64) + 2.0)) + (3 as f64))) + 4.0);
    println!("a: {}", a);
    let b = ((((((((1 as f64) + 0.5)) + (2 as f64))) + (3 as f64))) + (4 as f64));
    println!("b: {}", b);
    let c = ((1 as f64) + (((2 as f64) + (((3 as f64) + (((4 as f64) + 0.5)))))));
    println!("c: {}", c);
    let d = ((((1 as f64) * 2.0)) + (((3 * 4)) as f64));
    println!("d: {}", d);
    let e = ((((((2 as f64) * 3.0)) * (4 as f64))) * (5 as f64));
    println!("e: {}", e);
    let f = ((((10 as f64) / 2.0)) + (((8 - 3)) as f64));
    println!("f: {}", f);
    let g = (((((((1 + 2)) as f64) * 3.0) - (4 as f64))) / (2 as f64));
    println!("g: {}", g);
    let h = (((((1 + 2)) * 3)) + 4);
    println!("h (should be int): {}", h);
    let i = ((h as f64) + 0.1);
    println!("i (promoted from h): {}", i);
}