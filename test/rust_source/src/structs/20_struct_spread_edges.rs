#[derive(Clone, Default)]
struct __ZincAnonStruct_AnonStruct_a_i64_enabled_bool_extra_i64_name_String_z_i64 {
    a: i64,
    enabled: bool,
    extra: i64,
    name: String,
    z: i64,
}

#[derive(Clone, Default)]
struct __ZincAnonStruct_AnonStruct_a_i64_extra_i64_name_String {
    a: i64,
    extra: i64,
    name: String,
}

#[derive(Clone, Default)]
struct __ZincAnonStruct_AnonStruct_enabled_bool_name_String {
    enabled: bool,
    name: String,
}

struct structs_20_struct_spread_edges__BadName {
    pub name: i64,
    pub enabled: bool,
}

impl Default for structs_20_struct_spread_edges__BadName {
    fn default() -> Self {
        Self { name: 0, enabled: false }
    }
}

struct structs_20_struct_spread_edges__Config {
    pub a: i64,
    pub name: String,
    pub enabled: bool,
    pub ratio: f64,
}

impl Default for structs_20_struct_spread_edges__Config {
    fn default() -> Self {
        Self { a: 0, name: String::new(), enabled: false, ratio: 0.0 }
    }
}

struct structs_20_struct_spread_edges__FloatRatio {
    pub ratio: f64,
}

impl Default for structs_20_struct_spread_edges__FloatRatio {
    fn default() -> Self {
        Self { ratio: 0.0 }
    }
}

struct structs_20_struct_spread_edges__Nested {
    pub config: structs_20_struct_spread_edges__Config,
}

impl Default for structs_20_struct_spread_edges__Nested {
    fn default() -> Self {
        Self { config: Default::default() }
    }
}

fn structs_20_struct_spread_edges__ignored_config() -> structs_20_struct_spread_edges__Config {
    println!("ignore config");
    return structs_20_struct_spread_edges__Config { a: 9, name: String::from("ignored"), enabled: true, ratio: 9.5 };
}

fn structs_20_struct_spread_edges__noisy_config() -> structs_20_struct_spread_edges__Config {
    println!("make config");
    return structs_20_struct_spread_edges__Config { a: 8, name: String::from("made"), enabled: true, ratio: 6.5 };
}

fn main() {
    let base = structs_20_struct_spread_edges__Config { a: 1, name: String::from("base"), enabled: false, ratio: 1.5 };
    let bad = structs_20_struct_spread_edges__BadName { name: 404, enabled: true };
    let float_ratio = structs_20_struct_spread_edges__FloatRatio { ratio: 4.25 };
    let nested = structs_20_struct_spread_edges__Nested { config: base };
    let with_extra = __ZincAnonStruct_AnonStruct_a_i64_extra_i64_name_String { a: 4, name: String::from("anon"), extra: 99 };
    let fixed_bad = structs_20_struct_spread_edges__Config { a: 2, name: String::from("fixed"), enabled: bad.enabled, ratio: 2.5 };
    let from_nested = structs_20_struct_spread_edges__Config { a: 7, name: nested.config.name.clone(), enabled: nested.config.enabled, ratio: nested.config.ratio };
    let spread_ratio = structs_20_struct_spread_edges__Config { a: 3, name: String::from("ratio"), enabled: false, ratio: float_ratio.ratio };
    let named_ignores_extra = structs_20_struct_spread_edges__Config { a: with_extra.a, name: with_extra.name.clone(), enabled: true, ratio: 4.5 };
    let noisy = {
        let __zinc_field_spread_242_244 = structs_20_struct_spread_edges__noisy_config();
        structs_20_struct_spread_edges__Config { a: __zinc_field_spread_242_244.a, name: __zinc_field_spread_242_244.name.clone(), enabled: __zinc_field_spread_242_244.enabled, ratio: __zinc_field_spread_242_244.ratio }
    };
    let ignored = structs_20_struct_spread_edges__Config { a: 5, name: String::from("direct"), enabled: false, ratio: 5.5 };
    let anon_left = __ZincAnonStruct_AnonStruct_a_i64_extra_i64_name_String { a: 10, name: String::from("left"), extra: 1 };
    let anon_right = __ZincAnonStruct_AnonStruct_enabled_bool_name_String { name: String::from("right"), enabled: true };
    let anon_union = __ZincAnonStruct_AnonStruct_a_i64_enabled_bool_extra_i64_name_String_z_i64 { z: 0, a: 11, name: anon_right.name.clone(), extra: anon_left.extra, enabled: anon_right.enabled };
    println!("{}", fixed_bad.name);
    println!("{}", fixed_bad.enabled);
    println!("{}", from_nested.a);
    println!("{}", from_nested.name);
    println!("{}", spread_ratio.ratio);
    println!("{}", named_ignores_extra.name);
    println!("{}", named_ignores_extra.enabled);
    println!("{}", noisy.a);
    println!("{}", noisy.name);
    println!("{}", ignored.a);
    println!("{}", ignored.name);
    println!("{}", anon_union.z);
    println!("{}", anon_union.a);
    println!("{}", anon_union.name);
    println!("{}", anon_union.enabled);
    println!("{}", anon_union.extra);
}