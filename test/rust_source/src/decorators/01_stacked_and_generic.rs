use std::sync::{Arc, Mutex};

#[derive(Clone)]
struct __ZincClosureEnv_decorators_01_stacked_and_generic___lambda_decorators_01_stacked_and_generic____lambda_decorators_01_stacked_and_generic__labeler_String_60_89_i64_to_i64_72_88 {
    label: Arc<Mutex<String>>,
    f: Arc<Mutex<__ZincCallable_i64_to_i64>>,
}

#[derive(Clone)]
struct __ZincClosureEnv_decorators_01_stacked_and_generic___lambda_decorators_01_stacked_and_generic__labeler_String_60_89 {
    label: Arc<Mutex<String>>,
}

#[derive(Clone)]
struct __ZincClosureEnv_decorators_01_stacked_and_generic___lambda_decorators_01_stacked_and_generic__logged_i64_to_i64_19_35 {
    f: Arc<Mutex<__ZincCallable_i64_to_i64>>,
}

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
            Self::V0 => decorators_01_stacked_and_generic__echo_String__zinc_impl(arg_0),
        }
    }
}

#[derive(Clone)]
enum __ZincCallable_i64_to_i64 {
    Closed,
    V0(__ZincClosureEnv_decorators_01_stacked_and_generic___lambda_decorators_01_stacked_and_generic____lambda_decorators_01_stacked_and_generic__labeler_String_60_89_i64_to_i64_72_88),
    V1(__ZincClosureEnv_decorators_01_stacked_and_generic___lambda_decorators_01_stacked_and_generic__logged_i64_to_i64_19_35),
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
            Self::V0(env) => decorators_01_stacked_and_generic____lambda_decorators_01_stacked_and_generic____lambda_decorators_01_stacked_and_generic__labeler_String_60_89_i64_to_i64_72_88_i64(env.clone(), arg_0),
            Self::V1(env) => decorators_01_stacked_and_generic____lambda_decorators_01_stacked_and_generic__logged_i64_to_i64_19_35_i64(env.clone(), arg_0),
            Self::V2 => decorators_01_stacked_and_generic__echo_i64__zinc_impl(arg_0),
            Self::V3 => decorators_01_stacked_and_generic__inc_i64__zinc_impl(arg_0),
        }
    }
}

#[derive(Clone)]
enum __ZincCallable_i64_to_i64_to_i64_to_i64 {
    Closed,
    V0(__ZincClosureEnv_decorators_01_stacked_and_generic___lambda_decorators_01_stacked_and_generic__labeler_String_60_89),
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
            Self::V0(env) => decorators_01_stacked_and_generic____lambda_decorators_01_stacked_and_generic__labeler_String_60_89_i64_to_i64(env.clone(), arg_0),
        }
    }
}

fn decorators_01_stacked_and_generic____lambda_decorators_01_stacked_and_generic____lambda_decorators_01_stacked_and_generic__labeler_String_60_89_i64_to_i64_72_88_i64(__env: __ZincClosureEnv_decorators_01_stacked_and_generic___lambda_decorators_01_stacked_and_generic____lambda_decorators_01_stacked_and_generic__labeler_String_60_89_i64_to_i64_72_88, x: i64) -> i64 {
    let __zv_decorators_01_stacked_and_generic____lambda_decorators_01_stacked_and_generic____lambda_decorators_01_stacked_and_generic__labeler_String_60_89_i64_to_i64_72_88_i64_label_String = __env.label.clone();
    let __zv_decorators_01_stacked_and_generic____lambda_decorators_01_stacked_and_generic____lambda_decorators_01_stacked_and_generic__labeler_String_60_89_i64_to_i64_72_88_i64_f_i64_i64 = __env.f.clone();
    println!("{}", __zv_decorators_01_stacked_and_generic____lambda_decorators_01_stacked_and_generic____lambda_decorators_01_stacked_and_generic__labeler_String_60_89_i64_to_i64_72_88_i64_label_String.lock().unwrap().clone());
    return __zv_decorators_01_stacked_and_generic____lambda_decorators_01_stacked_and_generic____lambda_decorators_01_stacked_and_generic__labeler_String_60_89_i64_to_i64_72_88_i64_f_i64_i64.lock().unwrap().clone().call(x);
}

fn decorators_01_stacked_and_generic____lambda_decorators_01_stacked_and_generic__labeler_String_60_89_i64_to_i64(__env: __ZincClosureEnv_decorators_01_stacked_and_generic___lambda_decorators_01_stacked_and_generic__labeler_String_60_89, f: __ZincCallable_i64_to_i64) -> __ZincCallable_i64_to_i64 {
    let __zv_decorators_01_stacked_and_generic____lambda_decorators_01_stacked_and_generic__labeler_String_60_89_i64_to_i64_label_String = __env.label.clone();
    let __zv_decorators_01_stacked_and_generic____lambda_decorators_01_stacked_and_generic__labeler_String_60_89_i64_to_i64_f_i64_i64 = Arc::new(Mutex::new(f));
    return __ZincCallable_i64_to_i64::V0(__ZincClosureEnv_decorators_01_stacked_and_generic___lambda_decorators_01_stacked_and_generic____lambda_decorators_01_stacked_and_generic__labeler_String_60_89_i64_to_i64_72_88 { label: __zv_decorators_01_stacked_and_generic____lambda_decorators_01_stacked_and_generic__labeler_String_60_89_i64_to_i64_label_String.clone(), f: __zv_decorators_01_stacked_and_generic____lambda_decorators_01_stacked_and_generic__labeler_String_60_89_i64_to_i64_f_i64_i64.clone() });
}

fn decorators_01_stacked_and_generic__labeler_String(label: String) -> __ZincCallable_i64_to_i64_to_i64_to_i64 {
    let __zv_decorators_01_stacked_and_generic__labeler_String_label_String = Arc::new(Mutex::new(label));
    return __ZincCallable_i64_to_i64_to_i64_to_i64::V0(__ZincClosureEnv_decorators_01_stacked_and_generic___lambda_decorators_01_stacked_and_generic__labeler_String_60_89 { label: __zv_decorators_01_stacked_and_generic__labeler_String_label_String.clone() });
}

fn decorators_01_stacked_and_generic__logged_i64_to_i64(f: __ZincCallable_i64_to_i64) -> __ZincCallable_i64_to_i64 {
    let __zv_decorators_01_stacked_and_generic__logged_i64_to_i64_f_i64_i64 = Arc::new(Mutex::new(f));
    return __ZincCallable_i64_to_i64::V1(__ZincClosureEnv_decorators_01_stacked_and_generic___lambda_decorators_01_stacked_and_generic__logged_i64_to_i64_19_35 { f: __zv_decorators_01_stacked_and_generic__logged_i64_to_i64_f_i64_i64.clone() });
}

fn decorators_01_stacked_and_generic__inc_i64__zinc_impl(x: i64) -> i64 {
    return (x + 1);
}

fn decorators_01_stacked_and_generic__inc_i64(x: i64) -> i64 {
    let __zinc_decorated_0 = __ZincCallable_i64_to_i64::V3;
    let __zinc_decorated_1 = decorators_01_stacked_and_generic__logged_i64_to_i64(__zinc_decorated_0.clone());
    let __zinc_decorator_factory_2 = decorators_01_stacked_and_generic__labeler_String(String::from("outer"));
    let __zinc_decorated_2 = __zinc_decorator_factory_2.call(__zinc_decorated_1.clone());
    return __zinc_decorated_2.call(x);
}

fn decorators_01_stacked_and_generic____lambda_decorators_01_stacked_and_generic__logged_i64_to_i64_19_35_i64(__env: __ZincClosureEnv_decorators_01_stacked_and_generic___lambda_decorators_01_stacked_and_generic__logged_i64_to_i64_19_35, x: i64) -> i64 {
    let __zv_decorators_01_stacked_and_generic____lambda_decorators_01_stacked_and_generic__logged_i64_to_i64_19_35_i64_f_i64_i64 = __env.f.clone();
    println!("logged");
    return __zv_decorators_01_stacked_and_generic____lambda_decorators_01_stacked_and_generic__logged_i64_to_i64_19_35_i64_f_i64_i64.lock().unwrap().clone().call(x);
}

fn decorators_01_stacked_and_generic__identity_dec_String_to_String(f: __ZincCallable_String_to_String) -> __ZincCallable_String_to_String {
    return f;
}

fn decorators_01_stacked_and_generic__echo_String__zinc_impl(x: String) -> String {
    return x;
}

fn decorators_01_stacked_and_generic__echo_String(x: String) -> String {
    let __zinc_decorated_0 = __ZincCallable_String_to_String::V0;
    let __zinc_decorated_1 = decorators_01_stacked_and_generic__identity_dec_String_to_String(__zinc_decorated_0.clone());
    return __zinc_decorated_1.call(x);
}

fn decorators_01_stacked_and_generic__identity_dec_i64_to_i64(f: __ZincCallable_i64_to_i64) -> __ZincCallable_i64_to_i64 {
    return f;
}

fn decorators_01_stacked_and_generic__echo_i64__zinc_impl(x: i64) -> i64 {
    return x;
}

fn decorators_01_stacked_and_generic__echo_i64(x: i64) -> i64 {
    let __zinc_decorated_0 = __ZincCallable_i64_to_i64::V2;
    let __zinc_decorated_1 = decorators_01_stacked_and_generic__identity_dec_i64_to_i64(__zinc_decorated_0.clone());
    return __zinc_decorated_1.call(x);
}

fn main() {
    println!("{}", decorators_01_stacked_and_generic__inc_i64(3));
    println!("{}", decorators_01_stacked_and_generic__echo_i64(7));
    println!("{}", decorators_01_stacked_and_generic__echo_String(String::from("hi")));
}