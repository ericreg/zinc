struct structs_01_basic_fields__Counter {
    pub count: i64,
    pub step: i64,
    pub name: String,
}

impl Default for structs_01_basic_fields__Counter {
    fn default() -> Self {
        Self { count: 0, step: 1, name: String::new() }
    }
}

struct structs_01_basic_fields__Point {
    pub x: i32,
    pub y: i32,
}

impl Default for structs_01_basic_fields__Point {
    fn default() -> Self {
        Self { x: 0, y: 0 }
    }
}

fn main() {
    let p = structs_01_basic_fields__Point { x: 10, y: 20 };
    println!("{}", p.x);
    println!("{}", p.y);
    let c = structs_01_basic_fields__Counter { count: 0, step: 1, name: String::from("my_counter") };
    println!("{}", c.count);
    println!("{}", c.step);
}