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
            Self::V0 => decorators_03_constraints_and_annotations__annotated_i64__zinc_impl(arg_0),
            Self::V1 => decorators_03_constraints_and_annotations__constrained_i64__zinc_impl(arg_0),
        }
    }
}

fn decorators_03_constraints_and_annotations__identity_i64_i64_to_i64(f: __ZincCallable_i64_to_i64) -> __ZincCallable_i64_to_i64 {
    return f;
}

fn decorators_03_constraints_and_annotations__annotated_i64__zinc_impl(x: i64) -> i64 {
    return (x * 2);
}

fn decorators_03_constraints_and_annotations__annotated_i64(x: i64) -> i64 {
    let __zinc_decorated_0 = __ZincCallable_i64_to_i64::V0;
    let __zinc_decorated_1 = decorators_03_constraints_and_annotations__identity_i64_i64_to_i64(__zinc_decorated_0.clone());
    return __zinc_decorated_1.call(x);
}

fn decorators_03_constraints_and_annotations__identity_dec_i64_to_i64(f: __ZincCallable_i64_to_i64) -> __ZincCallable_i64_to_i64 {
    return f;
}

fn decorators_03_constraints_and_annotations__constrained_i64__zinc_impl(x: i64) -> i64 {
    return (x + 1);
}

fn decorators_03_constraints_and_annotations__constrained_i64(x: i64) -> i64 {
    let __zinc_decorated_0 = __ZincCallable_i64_to_i64::V1;
    let __zinc_decorated_1 = decorators_03_constraints_and_annotations__identity_dec_i64_to_i64(__zinc_decorated_0.clone());
    return __zinc_decorated_1.call(x);
}

fn main() {
    println!("{}", decorators_03_constraints_and_annotations__constrained_i64(4));
    println!("{}", decorators_03_constraints_and_annotations__annotated_i64(5));
}