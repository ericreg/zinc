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
            Self::V0 => decorators_04_qualified_import__score_i64__zinc_impl(arg_0),
        }
    }
}

#[derive(Clone)]
enum __ZincCallable_i64_to_i64_to_i64_to_i64 {
    Closed,
    V0,
}

impl Default for __ZincCallable_i64_to_i64_to_i64_to_i64 {
    fn default() -> Self {
        Self::Closed
    }
}

impl __ZincCallable_i64_to_i64_to_i64_to_i64 {
    fn call(&self, arg_0: __ZincCallable_i64_to_i64) -> __ZincCallable_i64_to_i64 {
        match self {
            Self::Closed => panic!("callable used after closed receive"),
            Self::V0 => decorators__lib_dec__identity_i64_i64_to_i64(arg_0),
        }
    }
}

fn decorators__lib_dec__identity_i64_i64_to_i64(f: __ZincCallable_i64_to_i64) -> __ZincCallable_i64_to_i64 {
    return f;
}

fn decorators__lib_dec__tag_String(label: String) -> __ZincCallable_i64_to_i64_to_i64_to_i64 {
    println!("{}", label);
    return __ZincCallable_i64_to_i64_to_i64_to_i64::V0;
}

fn decorators_04_qualified_import__score_i64__zinc_impl(x: i64) -> i64 {
    return (x * 2);
}

fn decorators_04_qualified_import__score_i64(x: i64) -> i64 {
    let __zinc_decorated_0 = __ZincCallable_i64_to_i64::V0;
    let __zinc_decorator_factory_1 = decorators__lib_dec__tag_String(String::from("qualified"));
    let __zinc_decorated_1 = __zinc_decorator_factory_1.call(__zinc_decorated_0.clone());
    return __zinc_decorated_1.call(x);
}

fn main() {
    println!("{}", decorators_04_qualified_import__score_i64(3));
}