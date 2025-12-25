struct Counter {
    pub count: i64,
    pub step: i64,
    pub name: String,
}

struct Point {
    pub x: i32,
    pub y: i32,
}

fn main() {
    let p = Point { x: 10, y: 20 };
    println!("{}", p.x);
    println!("{}", p.y);
    let c = Counter { count: 0, step: 1, name: String::from("my_counter") };
    println!("{}", c.count);
    println!("{}", c.step);
}