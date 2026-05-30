use std::sync::{Arc, Mutex};

#[derive(Clone)]
struct __ZincClosureEnv_closures_05_sibling_closures_shared_cell___lambda_closures_05_sibling_closures_shared_cell__make_pair_10_18 {
    count: Arc<Mutex<i64>>,
}

#[derive(Clone)]
struct __ZincClosureEnv_closures_05_sibling_closures_shared_cell___lambda_closures_05_sibling_closures_shared_cell__make_pair_21_29 {
    count: Arc<Mutex<i64>>,
}

#[derive(Clone)]
enum __ZincCallable_Unit_to_Unit {
    Closed,
    V0(__ZincClosureEnv_closures_05_sibling_closures_shared_cell___lambda_closures_05_sibling_closures_shared_cell__make_pair_10_18),
    V1(__ZincClosureEnv_closures_05_sibling_closures_shared_cell___lambda_closures_05_sibling_closures_shared_cell__make_pair_21_29),
}

impl Default for __ZincCallable_Unit_to_Unit {
    fn default() -> Self {
        Self::Closed
    }
}

impl __ZincCallable_Unit_to_Unit {
    fn call(&self, ) {
        match self {
            Self::Closed => panic!("callable used after closed receive"),
            Self::V0(env) => { closures_05_sibling_closures_shared_cell____lambda_closures_05_sibling_closures_shared_cell__make_pair_10_18(env.clone()); }
            Self::V1(env) => { closures_05_sibling_closures_shared_cell____lambda_closures_05_sibling_closures_shared_cell__make_pair_21_29(env.clone()); }
        }
    }
}

fn closures_05_sibling_closures_shared_cell____lambda_closures_05_sibling_closures_shared_cell__make_pair_10_18(__env: __ZincClosureEnv_closures_05_sibling_closures_shared_cell___lambda_closures_05_sibling_closures_shared_cell__make_pair_10_18) {
    let __zv_closures_05_sibling_closures_shared_cell____lambda_closures_05_sibling_closures_shared_cell__make_pair_10_18_count_i64 = __env.count.clone();
    let __zinc_captured_compound_17_17 = 1;
    *__zv_closures_05_sibling_closures_shared_cell____lambda_closures_05_sibling_closures_shared_cell__make_pair_10_18_count_i64.lock().unwrap() += __zinc_captured_compound_17_17;
}

fn closures_05_sibling_closures_shared_cell____lambda_closures_05_sibling_closures_shared_cell__make_pair_21_29(__env: __ZincClosureEnv_closures_05_sibling_closures_shared_cell___lambda_closures_05_sibling_closures_shared_cell__make_pair_21_29) {
    let __zv_closures_05_sibling_closures_shared_cell____lambda_closures_05_sibling_closures_shared_cell__make_pair_21_29_count_i64 = __env.count.clone();
    println!("{}", *__zv_closures_05_sibling_closures_shared_cell____lambda_closures_05_sibling_closures_shared_cell__make_pair_21_29_count_i64.lock().unwrap());
}

fn closures_05_sibling_closures_shared_cell__make_pair() -> (__ZincCallable_Unit_to_Unit, __ZincCallable_Unit_to_Unit) {
    let __zv_closures_05_sibling_closures_shared_cell__make_pair_count_i64 = Arc::new(Mutex::new(0));
    let inc = __ZincCallable_Unit_to_Unit::V0(__ZincClosureEnv_closures_05_sibling_closures_shared_cell___lambda_closures_05_sibling_closures_shared_cell__make_pair_10_18 { count: __zv_closures_05_sibling_closures_shared_cell__make_pair_count_i64.clone() });
    let read = __ZincCallable_Unit_to_Unit::V1(__ZincClosureEnv_closures_05_sibling_closures_shared_cell___lambda_closures_05_sibling_closures_shared_cell__make_pair_21_29 { count: __zv_closures_05_sibling_closures_shared_cell__make_pair_count_i64.clone() });
    return (inc, read);
}

fn main() {
    let (inc, read) = closures_05_sibling_closures_shared_cell__make_pair();
    inc.call();
    read.call();
    inc.call();
    read.call();
}