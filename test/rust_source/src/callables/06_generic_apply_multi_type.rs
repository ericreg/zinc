#[derive(Clone)]
enum __ZincCallable_String_to_String {
    Closed,
    V0,
}

impl Default for __ZincCallable_String_to_String {
    fn default() -> Self {
        Self::Closed
    }
}

impl __ZincCallable_String_to_String {
    fn call(&self, arg_0: String) -> String {
        match self {
            Self::Closed => panic!("callable used after closed receive"),
            Self::V0 => callables_06_generic_apply_multi_type__identity_String(arg_0),
        }
    }
}

#[derive(Clone)]
enum __ZincCallable_i64_to_i64 {
    Closed,
    V0,
}

impl Default for __ZincCallable_i64_to_i64 {
    fn default() -> Self {
        Self::Closed
    }
}

impl __ZincCallable_i64_to_i64 {
    fn call(&self, arg_0: i64) -> i64 {
        match self {
            Self::Closed => panic!("callable used after closed receive"),
            Self::V0 => callables_06_generic_apply_multi_type__identity_i64(arg_0),
        }
    }
}

fn callables_06_generic_apply_multi_type__identity_String(x: String) -> String {
    return x;
}

fn callables_06_generic_apply_multi_type__apply_unknown_to_unknown_String(f: __ZincCallable_String_to_String, x: String) -> String {
    return f.call(x);
}

fn callables_06_generic_apply_multi_type__identity_i64(x: i64) -> i64 {
    return x;
}

fn callables_06_generic_apply_multi_type__apply_unknown_to_unknown_i64(f: __ZincCallable_i64_to_i64, x: i64) -> i64 {
    return f.call(x);
}

fn main() {
    println!("{}", callables_06_generic_apply_multi_type__apply_unknown_to_unknown_i64(__ZincCallable_i64_to_i64::V0, 3));
    println!("{}", callables_06_generic_apply_multi_type__apply_unknown_to_unknown_String(__ZincCallable_String_to_String::V0, String::from("hi")));
}