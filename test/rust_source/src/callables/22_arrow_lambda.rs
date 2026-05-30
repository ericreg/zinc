use std::sync::{Arc, Mutex};

#[derive(Clone)]
struct __ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__main_90_96_i64_92_96 {
    x: Arc<Mutex<i64>>,
}

#[derive(Clone)]
struct __ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_118_122 {
}

#[derive(Clone)]
struct __ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_128_132 {
}

#[derive(Clone)]
struct __ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_157_160 {
}

#[derive(Clone)]
struct __ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_168_172 {
}

#[derive(Clone)]
struct __ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_36_40 {
}

#[derive(Clone)]
struct __ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_55_65 {
}

#[derive(Clone)]
struct __ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_90_96 {
}

#[derive(Clone)]
struct __ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__make_offset_i64_21_25 {
    base: Arc<Mutex<i64>>,
}

#[derive(Clone)]
enum __ZincCallable_Unit_to_i64 {
    Closed,
    V0(__ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_157_160),
}

impl Default for __ZincCallable_Unit_to_i64 {
    fn default() -> Self {
        Self::Closed
    }
}

impl __ZincCallable_Unit_to_i64 {
    fn call(&self, ) -> i64 {
        match self {
            Self::Closed => panic!("callable used after closed receive"),
            Self::V0(env) => callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__main_157_160(env.clone()),
        }
    }
}

#[derive(Clone)]
enum __ZincCallable_i64_i32_to_i64 {
    Closed,
    V0(__ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_55_65),
}

impl Default for __ZincCallable_i64_i32_to_i64 {
    fn default() -> Self {
        Self::Closed
    }
}

impl __ZincCallable_i64_i32_to_i64 {
    fn call(&self, arg_0: i64, arg_1: i32) -> i64 {
        match self {
            Self::Closed => panic!("callable used after closed receive"),
            Self::V0(env) => callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__main_55_65_i64_i32(env.clone(), arg_0, arg_1),
        }
    }
}

#[derive(Clone)]
enum __ZincCallable_i64_to_i64 {
    Closed,
    V0(__ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__main_90_96_i64_92_96),
    V1(__ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_118_122),
    V2(__ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_128_132),
    V3(__ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_168_172),
    V4(__ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_36_40),
    V5(__ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__make_offset_i64_21_25),
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
            Self::V0(env) => callables_22_arrow_lambda____lambda_callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__main_90_96_i64_92_96_i64(env.clone(), arg_0),
            Self::V1(env) => callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__main_118_122_i64(env.clone(), arg_0),
            Self::V2(env) => callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__main_128_132_i64(env.clone(), arg_0),
            Self::V3(env) => callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__main_168_172_i64(env.clone(), arg_0),
            Self::V4(env) => callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__main_36_40_i64(env.clone(), arg_0),
            Self::V5(env) => callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__make_offset_i64_21_25_i64(env.clone(), arg_0),
        }
    }
}

#[derive(Clone)]
enum __ZincCallable_i64_to_i64_to_i64 {
    Closed,
    V0(__ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_90_96),
}

impl Default for __ZincCallable_i64_to_i64_to_i64 {
    fn default() -> Self {
        Self::Closed
    }
}

impl __ZincCallable_i64_to_i64_to_i64 {
    fn call(&self, arg_0: i64) -> __ZincCallable_i64_to_i64 {
        match self {
            Self::Closed => panic!("callable used after closed receive"),
            Self::V0(env) => callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__main_90_96_i64(env.clone(), arg_0),
        }
    }
}

fn callables_22_arrow_lambda____lambda_callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__main_90_96_i64_92_96_i64(__env: __ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__main_90_96_i64_92_96, y: i64) -> i64 {
    let __zv_callables_22_arrow_lambda____lambda_callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__main_90_96_i64_92_96_i64_x_i64 = __env.x.clone();
    return (*__zv_callables_22_arrow_lambda____lambda_callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__main_90_96_i64_92_96_i64_x_i64.lock().unwrap() + y);
}

fn callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__main_118_122_i64(__env: __ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_118_122, x: i64) -> i64 {
    return (x + 1);
}

fn callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__main_128_132_i64(__env: __ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_128_132, x: i64) -> i64 {
    return (x * 2);
}

fn callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__main_157_160(__env: __ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_157_160) -> i64 {
    return 42;
}

fn callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__main_168_172_i64(__env: __ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_168_172, x: i64) -> i64 {
    return (x * 2);
}

fn callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__main_36_40_i64(__env: __ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_36_40, x: i64) -> i64 {
    return (x + 1);
}

fn callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__main_55_65_i64_i32(__env: __ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_55_65, x: i64, y: i32) -> i64 {
    return (x + 1);
}

fn callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__main_90_96_i64(__env: __ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_90_96, x: i64) -> __ZincCallable_i64_to_i64 {
    let __zv_callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__main_90_96_i64_x_i64 = Arc::new(Mutex::new(x));
    return __ZincCallable_i64_to_i64::V0(__ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__main_90_96_i64_92_96 { x: __zv_callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__main_90_96_i64_x_i64.clone() });
}

fn callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__make_offset_i64_21_25_i64(__env: __ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__make_offset_i64_21_25, x: i64) -> i64 {
    let __zv_callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__make_offset_i64_21_25_i64_base_i64 = __env.base.clone();
    return (x + *__zv_callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__make_offset_i64_21_25_i64_base_i64.lock().unwrap());
}

fn callables_22_arrow_lambda__apply_unknown_to_unknown_i64(f: __ZincCallable_i64_to_i64, x: i64) -> i64 {
    return f.call(x);
}

fn callables_22_arrow_lambda__make_offset_i64(base: i64) -> __ZincCallable_i64_to_i64 {
    let __zv_callables_22_arrow_lambda__make_offset_i64_base_i64 = Arc::new(Mutex::new(base));
    return __ZincCallable_i64_to_i64::V5(__ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__make_offset_i64_21_25 { base: __zv_callables_22_arrow_lambda__make_offset_i64_base_i64.clone() });
}

fn main() {
    println!("{}", callables_22_arrow_lambda__apply_unknown_to_unknown_i64(__ZincCallable_i64_to_i64::V4(__ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_36_40 {}), 4));
    let partial: __ZincCallable_i64_i32_to_i64 = __ZincCallable_i64_i32_to_i64::V0(__ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_55_65 {});
    println!("{}", partial.call(5, (2i32) as i32));
    let add10 = callables_22_arrow_lambda__make_offset_i64(10);
    println!("{}", add10.call(5));
    let maker = __ZincCallable_i64_to_i64_to_i64::V0(__ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_90_96 {});
    let add7 = maker.call(7);
    println!("{}", add7.call(8));
    let mut ops = vec![];
    ops.push(__ZincCallable_i64_to_i64::V1(__ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_118_122 {}));
    ops.push(__ZincCallable_i64_to_i64::V2(__ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_128_132 {}));
    println!("{}", ops[0].call(3));
    println!("{}", ops[1].call(3));
    println!("{}", __ZincCallable_Unit_to_i64::V0(__ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_157_160 {}).call());
    println!("{}", __ZincCallable_i64_to_i64::V3(__ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_168_172 {}).call(5));
}