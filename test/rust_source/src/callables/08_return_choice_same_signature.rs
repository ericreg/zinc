#[derive(Clone)]
enum __ZincCallable_i64_to_i64 {
    Closed,
    V0,
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
            Self::V0 => callables_08_return_choice_same_signature__double_i64(arg_0),
            Self::V1 => callables_08_return_choice_same_signature__inc_i64(arg_0),
        }
    }
}

fn callables_08_return_choice_same_signature__choose_bool(flag: bool) -> __ZincCallable_i64_to_i64 {
    if flag {
        return __ZincCallable_i64_to_i64::V1;
    }
    return __ZincCallable_i64_to_i64::V0;
}

fn callables_08_return_choice_same_signature__double_i64(x: i64) -> i64 {
    return (x * 2);
}

fn callables_08_return_choice_same_signature__inc_i64(x: i64) -> i64 {
    return (x + 1);
}

fn main() {
    println!("{}", callables_08_return_choice_same_signature__choose_bool(true).call(4));
    println!("{}", callables_08_return_choice_same_signature__choose_bool(false).call(4));
}