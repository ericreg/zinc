#[derive(Clone)]
enum __ZincCallable_i64_to_i64 {
    V0,
}

impl __ZincCallable_i64_to_i64 {
    fn call(&self, arg_0: i64) -> i64 {
        match self {
            Self::V0 => callables_02_lambda_array____lambda_13_22_i64(arg_0),
        }
    }
}

fn callables_02_lambda_array____lambda_13_22_i64(x: i64) -> i64 {
    return (x + 1);
}

fn main() {
    let mut ops = vec![];
    ops.push(__ZincCallable_i64_to_i64::V0);
    println!("{}", ops[0].call(10));
}