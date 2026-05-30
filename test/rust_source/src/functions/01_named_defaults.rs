use zinc_internal::{__ZincChannel};

const FUNCTIONS_01_NAMED_DEFAULTS__DEFAULT_COUNT: i32 = 7i32;

#[derive(Clone)]
struct __ZincClosureEnv_functions_01_named_defaults___lambda_functions_01_named_defaults__main_414_427 {
}

#[derive(Clone)]
enum __ZincCallable_i64_to_i64 {
    Closed,
    V0(__ZincClosureEnv_functions_01_named_defaults___lambda_functions_01_named_defaults__main_414_427),
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
            Self::V0(env) => functions_01_named_defaults____lambda_functions_01_named_defaults__main_414_427_i64(env.clone(), arg_0),
            Self::V1 => functions_01_named_defaults__inc_i64(arg_0),
        }
    }
}

struct functions_01_named_defaults__Counter {
    pub value: i64,
}

impl Default for functions_01_named_defaults__Counter {
    fn default() -> Self {
        Self { value: 0 }
    }
}

impl functions_01_named_defaults__Counter {
    fn add(&mut self, amount: i64) {
        self.value += amount;
    }
    fn value_or(&self, extra: i64) -> i64 {
        return (self.value + extra);
    }
}

fn functions_01_named_defaults____lambda_functions_01_named_defaults__main_414_427_i64(__env: __ZincClosureEnv_functions_01_named_defaults___lambda_functions_01_named_defaults__main_414_427, x: i64) -> i64 {
    return (x * 2);
}

fn functions_01_named_defaults__add_i32_i32(x: i32, y: i32) -> i32 {
    return (x + y);
}

fn functions_01_named_defaults__blend_f64_i32(x: f64, y: i32) -> f64 {
    return (x + (y as f64));
}

fn functions_01_named_defaults__blend_i32_i32(x: i32, y: i32) -> i32 {
    return (x + y);
}

fn functions_01_named_defaults__inc_i64(x: i64) -> i64 {
    return (x + 1);
}

fn functions_01_named_defaults__numeric_default_f64_i64(x: f64, y: i64) -> f64 {
    return (x + (y as f64));
}

fn functions_01_named_defaults__numeric_default_i32_f64(x: i32, y: f64) -> f64 {
    return ((x as f64) + y);
}

fn functions_01_named_defaults__numeric_default_i64_f64(x: i64, y: f64) -> f64 {
    return ((x as f64) + y);
}

fn functions_01_named_defaults__order3_i64_i64_i64(a: i64, b: i64, c: i64) -> i64 {
    return (((a * 10000) + (b * 100)) + c);
}

async fn functions_01_named_defaults__send_value_Channel_i64(out: __ZincChannel<i64>, value: i64) {
    out.send(value).await;
}

fn functions_01_named_defaults__tag_String_i32(prefix: String, count: i32) -> String {
    return String::from(format!("{}:{}", prefix, count));
}

#[tokio::main]
async fn main() {
    let mut __zinc_spawn_handles = Vec::new();
    println!("{}", functions_01_named_defaults__add_i32_i32(10, 20));
    println!("{}", functions_01_named_defaults__add_i32_i32(2, 3));
    println!("{}", functions_01_named_defaults__add_i32_i32(5, 6));
    println!("{}", functions_01_named_defaults__add_i32_i32(4, 20));
    println!("{}", functions_01_named_defaults__add_i32_i32(10, 6));
    println!("{}", functions_01_named_defaults__add_i32_i32(7, 20));
    println!("{}", functions_01_named_defaults__blend_i32_i32(10, 5));
    println!("{}", functions_01_named_defaults__blend_f64_i32(3.5, 5));
    println!("{}", functions_01_named_defaults__blend_f64_i32(2.5, 4));
    println!("{}", functions_01_named_defaults__numeric_default_i32_f64(10, 2.5));
    println!("{}", functions_01_named_defaults__numeric_default_f64_i64(1.5, 4));
    println!("{}", functions_01_named_defaults__numeric_default_i64_f64(2, 2.5));
    println!("{}", functions_01_named_defaults__order3_i64_i64_i64(1, 20, 300));
    println!("{}", functions_01_named_defaults__order3_i64_i64_i64(1, 2, 300));
    println!("{}", functions_01_named_defaults__order3_i64_i64_i64(1, 2, 3));
    println!("{}", functions_01_named_defaults__order3_i64_i64_i64(1, 2, 3));
    println!("{}", functions_01_named_defaults__tag_String_i32(String::from("id"), FUNCTIONS_01_NAMED_DEFAULTS__DEFAULT_COUNT));
    println!("{}", functions_01_named_defaults__tag_String_i32(String::from("item"), FUNCTIONS_01_NAMED_DEFAULTS__DEFAULT_COUNT));
    println!("{}", functions_01_named_defaults__tag_String_i32(String::from("row"), 9));
    let ch = __ZincChannel::<i64>::unbounded();
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = ch.clone(); async move { functions_01_named_defaults__send_value_Channel_i64(__zinc_spawn_arg_0.clone(), 8).await; } }));
    println!("{}", ch.recv().await);
    let ch2 = __ZincChannel::<i64>::unbounded();
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = ch2.clone(); async move { functions_01_named_defaults__send_value_Channel_i64(__zinc_spawn_arg_0.clone(), 13).await; } }));
    println!("{}", ch2.recv().await);
    let lambda = __ZincCallable_i64_to_i64::V0(__ZincClosureEnv_functions_01_named_defaults___lambda_functions_01_named_defaults__main_414_427 {});
    println!("{}", lambda.call(4));
    println!("{}", lambda.call(6));
    let mut counter = functions_01_named_defaults__Counter { value: 0 };
    counter.add(1);
    counter.add(4);
    println!("{}", counter.value_or(5));
    counter.add(2);
    counter.add(3);
    println!("{}", counter.value_or(0));
    println!("{}", counter.value_or(1));
    let f = __ZincCallable_i64_to_i64::V1;
    println!("{}", f.call(9));
    println!("{}", f.call(3));
    println!("{}", f.call(1));
    while let Some(__zinc_spawn_handle) = __zinc_spawn_handles.pop() {
        __zinc_spawn_handle.await.unwrap();
    }
}