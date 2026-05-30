#[derive(Clone, Default)]
struct __ZincAnonStruct_AnonStruct_height_i64_width_i64 {
    height: i64,
    width: i64,
}

fn structs_15_anon_function_param_return__area_AnonStruct_height_i64_width_i64(rect: __ZincAnonStruct_AnonStruct_height_i64_width_i64) -> i64 {
    return (rect.width * rect.height);
}

fn structs_15_anon_function_param_return__grow_AnonStruct_height_i64_width_i64(rect: __ZincAnonStruct_AnonStruct_height_i64_width_i64) -> __ZincAnonStruct_AnonStruct_height_i64_width_i64 {
    return __ZincAnonStruct_AnonStruct_height_i64_width_i64 { height: (rect.height + 1), width: (rect.width + 2) };
}

fn main() {
    let measured = __ZincAnonStruct_AnonStruct_height_i64_width_i64 { height: 4, width: 3 };
    println!("{}", structs_15_anon_function_param_return__area_AnonStruct_height_i64_width_i64(measured));
    let resized = structs_15_anon_function_param_return__grow_AnonStruct_height_i64_width_i64(__ZincAnonStruct_AnonStruct_height_i64_width_i64 { height: 4, width: 3 });
    println!("{}", resized.width);
    println!("{}", resized.height);
}