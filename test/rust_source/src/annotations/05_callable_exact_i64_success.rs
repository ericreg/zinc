#[derive(Clone)]
struct __ZincClosureEnv_annotations_05_callable_exact_i64_success___lambda_annotations_05_callable_exact_i64_success__main_56_67 {
}

#[derive(Clone)]
enum __ZincCallable_i64_to_i64 {
    Closed,
    V0(__ZincClosureEnv_annotations_05_callable_exact_i64_success___lambda_annotations_05_callable_exact_i64_success__main_56_67),
    V1,
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
            Self::V0(env) => annotations_05_callable_exact_i64_success____lambda_annotations_05_callable_exact_i64_success__main_56_67_i64(env.clone(), arg_0),
            Self::V1 => annotations_05_callable_exact_i64_success__inc_i64(arg_0),
        }
    }
}

fn annotations_05_callable_exact_i64_success____lambda_annotations_05_callable_exact_i64_success__main_56_67_i64(__env: __ZincClosureEnv_annotations_05_callable_exact_i64_success___lambda_annotations_05_callable_exact_i64_success__main_56_67, value: i64) -> i64 {
    return (value + 2);
}

fn annotations_05_callable_exact_i64_success__inc_i64(x: i64) -> i64 {
    return (x + 1);
}

fn annotations_05_callable_exact_i64_success__apply_twice_i64_to_unknown_i64(f: __ZincCallable_i64_to_i64, x: i64) -> i64 {
    return f.call(f.call(x));
}

fn main() {
    println!("{}", annotations_05_callable_exact_i64_success__apply_twice_i64_to_unknown_i64(__ZincCallable_i64_to_i64::V1, 4));
    println!("{}", annotations_05_callable_exact_i64_success__apply_twice_i64_to_unknown_i64(__ZincCallable_i64_to_i64::V0(__ZincClosureEnv_annotations_05_callable_exact_i64_success___lambda_annotations_05_callable_exact_i64_success__main_56_67 {}), 4));
}