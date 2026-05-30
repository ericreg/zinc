#[derive(Clone, Default)]
struct __ZincAnonStruct_AnonStruct_x_i64_y_i64 {
    x: i64,
    y: i64,
}

struct structs_18_anon_named_struct_field__Holder {
    pub point: __ZincAnonStruct_AnonStruct_x_i64_y_i64,
    pub label: String,
}

impl Default for structs_18_anon_named_struct_field__Holder {
    fn default() -> Self {
        Self { point: Default::default(), label: String::new() }
    }
}

fn structs_18_anon_named_struct_field__show_Struct_structs_18_anon_named_struct_field_Holder(holder: structs_18_anon_named_struct_field__Holder) {
    println!("{}", holder.point.x);
    println!("{}", holder.label);
}

fn main() {
    let holder = structs_18_anon_named_struct_field__Holder { point: __ZincAnonStruct_AnonStruct_x_i64_y_i64 { y: 9, x: 7 }, label: String::from("origin") };
    println!("{}", holder.point.y);
    structs_18_anon_named_struct_field__show_Struct_structs_18_anon_named_struct_field_Holder(holder);
}