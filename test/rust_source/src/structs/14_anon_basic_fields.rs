#[derive(Clone, Default)]
struct __ZincAnonStruct_AnonStruct_empty {
}

#[derive(Clone, Default)]
struct __ZincAnonStruct_AnonStruct_x_i64_y_i64 {
    x: i64,
    y: i64,
}

fn main() {
    let mut point = __ZincAnonStruct_AnonStruct_x_i64_y_i64 { x: 10, y: 20 };
    point.x = (point.x + 5);
    println!("{}", point.x);
    println!("{}", point.y);
    let empty = __ZincAnonStruct_AnonStruct_empty {  };
    println!("empty ready");
}