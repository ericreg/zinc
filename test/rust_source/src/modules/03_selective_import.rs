const MODULES__LIB_SHAPES__SCALE: i64 = 2;

struct modules__lib_shapes__Point {
    pub x: i64,
    pub y: i64,
}

fn modules__lib_shapes__double_i64(x: i64) -> i64 {
    return (x * MODULES__LIB_SHAPES__SCALE);
}

fn main() {
    let point = modules__lib_shapes__Point { x: modules__lib_shapes__double_i64(2), y: 9 };
    println!("{}", point.x);
    println!("{}", point.y);
}