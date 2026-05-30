#[derive(Clone, Default)]
struct __ZincAnonStruct_AnonStruct_value_f32 {
    value: f32,
}

#[derive(Clone, Default)]
struct __ZincAnonStruct_AnonStruct_value_i32 {
    value: i32,
}

// infer-backed struct family annotations_07_type_alternatives__Measure uses synthesized concrete shapes

fn annotations_07_type_alternatives__keep_numeric_attr_i64(x: i64) -> i64 {
    return x;
}

fn annotations_07_type_alternatives__keep_numeric_i64(x: i64) -> i64 {
    return x;
}

fn annotations_07_type_alternatives__keep_specific_f32(x: f32) -> f32 {
    return x;
}

fn annotations_07_type_alternatives__keep_specific_i32(x: i32) -> i32 {
    return x;
}

fn main() {
    let whole: i32 = 4;
    let ratio: f32 = 1.5;
    let whole_measure = __ZincAnonStruct_AnonStruct_value_i32 { value: whole };
    let ratio_measure = __ZincAnonStruct_AnonStruct_value_f32 { value: ratio };
    println!("{}", annotations_07_type_alternatives__keep_specific_i32(whole));
    println!("{}", annotations_07_type_alternatives__keep_specific_f32(ratio));
    println!("{}", annotations_07_type_alternatives__keep_numeric_i64(9));
    println!("{}", annotations_07_type_alternatives__keep_numeric_attr_i64(10));
    println!("{}", whole_measure.value);
    println!("{}", ratio_measure.value);
}