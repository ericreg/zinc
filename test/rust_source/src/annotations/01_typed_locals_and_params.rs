struct annotations_01_typed_locals_and_params__Pair {
    pub a: i32,
    pub b: f32,
}

impl Default for annotations_01_typed_locals_and_params__Pair {
    fn default() -> Self {
        Self { a: 0, b: 0.0 }
    }
}

fn annotations_01_typed_locals_and_params__add_f32_f32_i64(x: f32, y: i64) -> f32 {
    return (x + (y as f32));
}

fn annotations_01_typed_locals_and_params__add_i32_i32_i32(x: i32, y: i32) -> i32 {
    return (x + y);
}

fn main() {
    let mut x: i32 = 5;
    x = 4;
    let y = annotations_01_typed_locals_and_params__add_i32_i32_i32(x, 6);
    println!("{}", y);
    let x: f32 = 5.0;
    let z = annotations_01_typed_locals_and_params__add_f32_f32_i64(x, 3);
    println!("{}", z);
    let pair = annotations_01_typed_locals_and_params__Pair { a: 7, b: 1.5 };
    println!("{}", pair.a);
    println!("{}", pair.b);
}