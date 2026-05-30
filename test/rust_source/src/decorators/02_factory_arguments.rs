#[derive(Clone)]
enum __ZincCallable_i64_to_i64 {
    Closed,
    V0,
    V1,
    V2,
    V3,
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
            Self::V0 => decorators_02_factory_arguments__direct_default_i64__zinc_impl(arg_0),
            Self::V1 => decorators_02_factory_arguments__empty_value_i64__zinc_impl(arg_0),
            Self::V2 => decorators_02_factory_arguments__named_i64__zinc_impl(arg_0),
            Self::V3 => decorators_02_factory_arguments__positional_i64__zinc_impl(arg_0),
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
            Self::V0 => decorators_02_factory_arguments__identity_i64_i64_to_i64(arg_0),
        }
    }
}

fn decorators_02_factory_arguments__identity_i64_i64_to_i64(f: __ZincCallable_i64_to_i64) -> __ZincCallable_i64_to_i64 {
    return f;
}

fn decorators_02_factory_arguments__announce_String_i64_String(label: String, times: i64, suffix: String) -> __ZincCallable_i64_to_i64_to_i64_to_i64 {
    println!("{}", label);
    println!("{}", times);
    println!("{}", suffix);
    return __ZincCallable_i64_to_i64_to_i64_to_i64::V0;
}

fn decorators_02_factory_arguments__direct_label_i64_to_i64_String(f: __ZincCallable_i64_to_i64, label: String) -> __ZincCallable_i64_to_i64 {
    println!("{}", label);
    return f;
}

fn decorators_02_factory_arguments__direct_default_i64__zinc_impl(x: i64) -> i64 {
    return (x + 100);
}

fn decorators_02_factory_arguments__direct_default_i64(x: i64) -> i64 {
    let __zinc_decorated_0 = __ZincCallable_i64_to_i64::V0;
    let __zinc_decorated_1 = decorators_02_factory_arguments__direct_label_i64_to_i64_String(__zinc_decorated_0.clone(), String::from("direct-default"));
    return __zinc_decorated_1.call(x);
}

fn decorators_02_factory_arguments__empty_factory() -> __ZincCallable_i64_to_i64_to_i64_to_i64 {
    println!("empty");
    return __ZincCallable_i64_to_i64_to_i64_to_i64::V0;
}

fn decorators_02_factory_arguments__empty_value_i64__zinc_impl(x: i64) -> i64 {
    return (x + 30);
}

fn decorators_02_factory_arguments__empty_value_i64(x: i64) -> i64 {
    let __zinc_decorated_0 = __ZincCallable_i64_to_i64::V1;
    let __zinc_decorator_factory_1 = decorators_02_factory_arguments__empty_factory();
    let __zinc_decorated_1 = __zinc_decorator_factory_1.call(__zinc_decorated_0.clone());
    return __zinc_decorated_1.call(x);
}

fn decorators_02_factory_arguments__named_i64__zinc_impl(x: i64) -> i64 {
    return (x + 10);
}

fn decorators_02_factory_arguments__named_i64(x: i64) -> i64 {
    let __zinc_decorated_0 = __ZincCallable_i64_to_i64::V2;
    let __zinc_decorator_factory_1 = decorators_02_factory_arguments__announce_String_i64_String(String::from("named"), 1, String::from("?"));
    let __zinc_decorated_1 = __zinc_decorator_factory_1.call(__zinc_decorated_0.clone());
    return __zinc_decorated_1.call(x);
}

fn decorators_02_factory_arguments__positional_i64__zinc_impl(x: i64) -> i64 {
    return (x + 20);
}

fn decorators_02_factory_arguments__positional_i64(x: i64) -> i64 {
    let __zinc_decorated_0 = __ZincCallable_i64_to_i64::V3;
    let __zinc_decorator_factory_1 = decorators_02_factory_arguments__announce_String_i64_String(String::from("positional"), 2, String::from("!"));
    let __zinc_decorated_1 = __zinc_decorator_factory_1.call(__zinc_decorated_0.clone());
    return __zinc_decorated_1.call(x);
}

fn main() {
    println!("{}", decorators_02_factory_arguments__named_i64(1));
    println!("{}", decorators_02_factory_arguments__positional_i64(2));
    println!("{}", decorators_02_factory_arguments__direct_default_i64(3));
    println!("{}", decorators_02_factory_arguments__empty_value_i64(4));
}