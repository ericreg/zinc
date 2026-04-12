fn main() {
    let a = ((((1 as f64) + 2.0)) > (3 as f64));
    println!("(1 + 2.0) > 3: {}", a);
    let b = ((5 as f64) < 4.5);
    println!("5 < 4.5: {}", b);
    let c = (3.0 == (3 as f64));
    println!("3.0 == 3: {}", c);
    let d = ((((10 as f64) / 2.0)) >= (5 as f64));
    println!("(10 / 2.0) >= 5: {}", d);
    let x = 1.5;
    let e = (x > (1 as f64));
    println!("1.5 > 1: {}", e);
    let f = (x < (2 as f64));
    println!("1.5 < 2: {}", f);
    let g = (((((1 as f64) + 0.5)) > (1 as f64)) && ((((2 as f64) + 0.5)) > (2 as f64)));
    println!("both comparisons true: {}", g);
    let h = (2.5 != (2 as f64));
    println!("2.5 != 2: {}", h);
    let i = (2.0 != (2 as f64));
    println!("2.0 != 2: {}", i);
    let j = (0.0 == (0 as f64));
    println!("0.0 == 0: {}", j);
    let k = (((-1) as f64) < 0.0);
    println!("-1 < 0.0: {}", k);
}