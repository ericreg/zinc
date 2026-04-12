fn main() {
    let mut a = vec![];
    a.push(1);
    println!("a[0]: {}", a[0]);
    let mut b = vec![];
    b.push(3.14);
    println!("b[0]: {}", b[0]);
    let mut c = vec![];
    c.push(true);
    println!("c[0]: {}", c[0]);
    let mut d = vec![];
    d.push("hello");
    println!("d[0]: {}", d[0]);
    let e = vec![1, 2, 3];
    println!("e[0]: {}", e[0]);
    let mut f = vec![];
    f.push(42);
    f.push(43);
    println!("f[0]: {}", f[0]);
    println!("f[1]: {}", f[1]);
    println!("test complete");
}