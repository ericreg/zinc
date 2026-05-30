fn annotations_08_rust_numeric_literals__id_f32_f32(x: f32) -> f32 {
    return x;
}

fn annotations_08_rust_numeric_literals__id_f64_f64(x: f64) -> f64 {
    return x;
}

fn annotations_08_rust_numeric_literals__id_i16_i16(x: i16) -> i16 {
    return x;
}

fn annotations_08_rust_numeric_literals__id_u8_u8(x: u8) -> u8 {
    return x;
}

fn annotations_08_rust_numeric_literals__id_usize_usize(x: usize) -> usize {
    return x;
}

fn main() {
    println!("{}", 1_000);
    println!("{}", 123_);
    println!("{}", 0b________1);
    println!("{}", 0b1111_0000_u16);
    println!("{}", annotations_08_rust_numeric_literals__id_i16_i16(0o70_i16));
    println!("{}", annotations_08_rust_numeric_literals__id_u8_u8(0xff_u8));
    println!("{}", 0x01_f32);
    println!("{}", annotations_08_rust_numeric_literals__id_usize_usize(5usize));
    println!("{}", 2.);
    println!("{}", 1e_6);
    println!("{}", 1e+_9);
    println!("{}", annotations_08_rust_numeric_literals__id_f32_f32(5_f32));
    println!("{}", annotations_08_rust_numeric_literals__id_f32_f32(123.456_f32));
    println!("{}", annotations_08_rust_numeric_literals__id_f64_f64(12E+99_f64));
}