#[derive(Clone, Default)]
struct __ZincAnonStruct_AnonStruct_a_i64_enabled_bool_extra_i64_name_String {
    a: i64,
    enabled: bool,
    extra: i64,
    name: String,
}

#[derive(Clone, Default)]
struct __ZincAnonStruct_AnonStruct_a_i64_enabled_bool_name_String {
    a: i64,
    enabled: bool,
    name: String,
}

#[derive(Clone, Default)]
struct __ZincAnonStruct_AnonStruct_x_i64_y_i64 {
    x: i64,
    y: i64,
}

struct structs_19_struct_spread__Config {
    pub a: i64,
    pub name: String,
    pub enabled: bool,
    pub ratio: f64,
}

impl Default for structs_19_struct_spread__Config {
    fn default() -> Self {
        Self { a: 0, name: String::new(), enabled: false, ratio: 0.0 }
    }
}

struct structs_19_struct_spread__PartialConfig {
    pub name: String,
    pub enabled: bool,
}

impl Default for structs_19_struct_spread__PartialConfig {
    fn default() -> Self {
        Self { name: String::new(), enabled: false }
    }
}

fn structs_19_struct_spread__make_config() -> structs_19_struct_spread__Config {
    return structs_19_struct_spread__Config { a: 7, name: String::from("made"), enabled: true, ratio: 4.5 };
}

fn main() {
    let base = structs_19_struct_spread__Config { a: 1, name: String::from("base"), enabled: false, ratio: 1.5 };
    let partial = structs_19_struct_spread__PartialConfig { name: String::from("partial"), enabled: true };
    let right_override = structs_19_struct_spread__Config { a: 2, name: String::from("right"), enabled: base.enabled, ratio: base.ratio };
    let left_override = structs_19_struct_spread__Config { a: base.a, name: base.name.clone(), enabled: base.enabled, ratio: base.ratio };
    let filled = structs_19_struct_spread__Config { a: 4, name: partial.name.clone(), enabled: partial.enabled, ratio: 2.5 };
    let layered = structs_19_struct_spread__Config { a: filled.a, name: filled.name.clone(), enabled: false, ratio: filled.ratio };
    let made = {
        let __zinc_field_spread_154_156 = structs_19_struct_spread__make_config();
        structs_19_struct_spread__Config { a: 8, name: __zinc_field_spread_154_156.name.clone(), enabled: __zinc_field_spread_154_156.enabled, ratio: __zinc_field_spread_154_156.ratio }
    };
    let duplicate = structs_19_struct_spread__Config { a: 6, name: String::from("dupe"), enabled: true, ratio: 3.5 };
    let anon_base = __ZincAnonStruct_AnonStruct_a_i64_enabled_bool_name_String { a: 5, name: String::from("anon"), enabled: true };
    let anon = __ZincAnonStruct_AnonStruct_a_i64_enabled_bool_extra_i64_name_String { a: anon_base.a, name: String::from("later"), enabled: anon_base.enabled, extra: 9 };
    let anon_duplicate = __ZincAnonStruct_AnonStruct_x_i64_y_i64 { x: 3, y: 2 };
    println!("{}", right_override.a);
    println!("{}", right_override.name);
    println!("{}", left_override.a);
    println!("{}", left_override.name);
    println!("{}", filled.name);
    println!("{}", filled.enabled);
    println!("{}", layered.a);
    println!("{}", layered.name);
    println!("{}", layered.enabled);
    println!("{}", made.a);
    println!("{}", made.name);
    println!("{}", duplicate.name);
    println!("{}", duplicate.enabled);
    println!("{}", anon.a);
    println!("{}", anon.name);
    println!("{}", anon.extra);
    println!("{}", anon_duplicate.x);
}