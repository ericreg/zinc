fn annotations_04_mixed_specialization_with_annotated_slot__add_to_float_f32_i32(x: f32, y: i32) -> f32 {
    return (x + (y as f32));
}

fn annotations_04_mixed_specialization_with_annotated_slot__add_to_float_f32_i64(x: f32, y: i64) -> f32 {
    return (x + (y as f32));
}

fn main() {
    let base: f32 = 1.5;
    let step: i32 = 3;
    println!("{}", annotations_04_mixed_specialization_with_annotated_slot__add_to_float_f32_i64(base, 2));
    println!("{}", annotations_04_mixed_specialization_with_annotated_slot__add_to_float_f32_i32(base, step));
}