#[derive(Clone)]
enum __ZincCallable_i64_to_i64 {
    V0,
    V1,
}

impl __ZincCallable_i64_to_i64 {
    fn call(&self, arg_0: i64) -> i64 {
        match self {
            Self::V0 => callables_13_named_function_array__double_i64(arg_0),
            Self::V1 => callables_13_named_function_array__inc_i64(arg_0),
        }
    }
}

fn callables_13_named_function_array__double_i64(x: i64) -> i64 {
    return (x * 2);
}

fn callables_13_named_function_array__inc_i64(x: i64) -> i64 {
    return (x + 1);
}

fn main() {
    let mut ops = vec![];
    ops.push(__ZincCallable_i64_to_i64::V1);
    ops.push(__ZincCallable_i64_to_i64::V0);
    println!("{}", ops[0].call(4));
    println!("{}", ops[1].call(4));
}