use std::sync::{Arc, Mutex};

#[derive(Clone)]
struct __ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__main_263_269_i64_265_269 {
    x: Arc<Mutex<i64>>,
}

#[derive(Clone)]
struct __ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__make_chain_i64_47_55_i64_49_55 {
    x: Arc<Mutex<i64>>,
    y: Arc<Mutex<i64>>,
}

#[derive(Clone)]
struct __ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__choose_bool_27_31 {
}

#[derive(Clone)]
struct __ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__choose_bool_34_38 {
}

#[derive(Clone)]
struct __ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__main_105_115 {
}

#[derive(Clone)]
struct __ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__main_135_145 {
}

#[derive(Clone)]
struct __ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__main_165_173 {
}

#[derive(Clone)]
struct __ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__main_188_193 {
    seed: Arc<Mutex<i64>>,
}

#[derive(Clone)]
struct __ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__main_206_210 {
    offset: Arc<Mutex<i64>>,
}

#[derive(Clone)]
struct __ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__main_220_224 {
}

#[derive(Clone)]
struct __ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__main_263_269 {
}

#[derive(Clone)]
struct __ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__main_285_303 {
}

#[derive(Clone)]
struct __ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__main_330_334 {
}

#[derive(Clone)]
struct __ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__main_344_352 {
}

#[derive(Clone)]
struct __ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__main_368_377 {
}

#[derive(Clone)]
struct __ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__main_392_402 {
}

#[derive(Clone)]
struct __ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__main_83_89 {
}

#[derive(Clone)]
struct __ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__make_chain_i64_47_55 {
    x: Arc<Mutex<i64>>,
}

#[derive(Clone)]
enum __ZincCallable_String_i32_to_i64 {
    Closed,
    V0(__ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__main_165_173),
}

impl Default for __ZincCallable_String_i32_to_i64 {
    fn default() -> Self {
        Self::Closed
    }
}

impl __ZincCallable_String_i32_to_i64 {
    fn call(&self, arg_0: String, arg_1: i32) -> i64 {
        match self {
            Self::Closed => panic!("callable used after closed receive"),
            Self::V0(env) => callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__main_165_173_String_i32(env.clone(), arg_0, arg_1),
        }
    }
}

#[derive(Clone)]
enum __ZincCallable_Unit_to_i64 {
    Closed,
    V0(__ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__main_188_193),
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
            Self::V0(env) => callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__main_188_193(env.clone()),
        }
    }
}

#[derive(Clone)]
enum __ZincCallable_bool_i64_to_i64 {
    Closed,
    V0(__ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__main_285_303),
}

impl Default for __ZincCallable_bool_i64_to_i64 {
    fn default() -> Self {
        Self::Closed
    }
}

impl __ZincCallable_bool_i64_to_i64 {
    fn call(&self, arg_0: bool, arg_1: i64) -> i64 {
        match self {
            Self::Closed => panic!("callable used after closed receive"),
            Self::V0(env) => callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__main_285_303_bool_i64(env.clone(), arg_0, arg_1),
        }
    }
}

#[derive(Clone)]
enum __ZincCallable_i32_i64_to_i64 {
    Closed,
    V0(__ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__main_135_145),
}

impl Default for __ZincCallable_i32_i64_to_i64 {
    fn default() -> Self {
        Self::Closed
    }
}

impl __ZincCallable_i32_i64_to_i64 {
    fn call(&self, arg_0: i32, arg_1: i64) -> i64 {
        match self {
            Self::Closed => panic!("callable used after closed receive"),
            Self::V0(env) => callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__main_135_145_i32_i64(env.clone(), arg_0, arg_1),
        }
    }
}

#[derive(Clone)]
enum __ZincCallable_i64_i32_to_i64 {
    Closed,
    V0(__ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__main_105_115),
    V1(__ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__main_392_402),
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
            Self::V0(env) => callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__main_105_115_i64_i32(env.clone(), arg_0, arg_1),
            Self::V1(env) => callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__main_392_402_i64_i32(env.clone(), arg_0, arg_1),
        }
    }
}

#[derive(Clone)]
enum __ZincCallable_i64_i64_to_i64 {
    Closed,
    V0(__ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__main_344_352),
    V1(__ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__main_368_377),
}

impl Default for __ZincCallable_i64_i64_to_i64 {
    fn default() -> Self {
        Self::Closed
    }
}

impl __ZincCallable_i64_i64_to_i64 {
    fn call(&self, arg_0: i64, arg_1: i64) -> i64 {
        match self {
            Self::Closed => panic!("callable used after closed receive"),
            Self::V0(env) => callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__main_344_352_i64_i64(env.clone(), arg_0, arg_1),
            Self::V1(env) => callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__main_368_377_i64_i64(env.clone(), arg_0, arg_1),
        }
    }
}

#[derive(Clone)]
enum __ZincCallable_i64_to_i64 {
    Closed,
    V0(__ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__main_263_269_i64_265_269),
    V1(__ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__make_chain_i64_47_55_i64_49_55),
    V2(__ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__choose_bool_27_31),
    V3(__ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__choose_bool_34_38),
    V4(__ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__main_206_210),
    V5(__ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__main_220_224),
    V6(__ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__main_330_334),
    V7(__ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__main_83_89),
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
            Self::V0(env) => callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__main_263_269_i64_265_269_i64(env.clone(), arg_0),
            Self::V1(env) => callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__make_chain_i64_47_55_i64_49_55_i64(env.clone(), arg_0),
            Self::V2(env) => callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__choose_bool_27_31_i64(env.clone(), arg_0),
            Self::V3(env) => callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__choose_bool_34_38_i64(env.clone(), arg_0),
            Self::V4(env) => callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__main_206_210_i64(env.clone(), arg_0),
            Self::V5(env) => callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__main_220_224_i64(env.clone(), arg_0),
            Self::V6(env) => callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__main_330_334_i64(env.clone(), arg_0),
            Self::V7(env) => callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__main_83_89_i64(env.clone(), arg_0),
        }
    }
}

#[derive(Clone)]
enum __ZincCallable_i64_to_i64_to_i64 {
    Closed,
    V0(__ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__main_263_269),
    V1(__ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__make_chain_i64_47_55),
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
            Self::V0(env) => callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__main_263_269_i64(env.clone(), arg_0),
            Self::V1(env) => callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__make_chain_i64_47_55_i64(env.clone(), arg_0),
        }
    }
}

fn callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__main_263_269_i64_265_269_i64(__env: __ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__main_263_269_i64_265_269, y: i64) -> i64 {
    let __zv_callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__main_263_269_i64_265_269_i64_x_i64 = __env.x.clone();
    return (*__zv_callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__main_263_269_i64_265_269_i64_x_i64.lock().unwrap() * y);
}

fn callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__make_chain_i64_47_55_i64_49_55_i64(__env: __ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__make_chain_i64_47_55_i64_49_55, z: i64) -> i64 {
    let __zv_callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__make_chain_i64_47_55_i64_49_55_i64_x_i64 = __env.x.clone();
    let __zv_callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__make_chain_i64_47_55_i64_49_55_i64_y_i64 = __env.y.clone();
    return ((*__zv_callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__make_chain_i64_47_55_i64_49_55_i64_x_i64.lock().unwrap() + *__zv_callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__make_chain_i64_47_55_i64_49_55_i64_y_i64.lock().unwrap()) + z);
}

fn callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__choose_bool_27_31_i64(__env: __ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__choose_bool_27_31, x: i64) -> i64 {
    return (x + 1);
}

fn callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__choose_bool_34_38_i64(__env: __ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__choose_bool_34_38, x: i64) -> i64 {
    return (x + 2);
}

fn callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__main_105_115_i64_i32(__env: __ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__main_105_115, x: i64, y: i32) -> i64 {
    return (x + 1);
}

fn callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__main_135_145_i32_i64(__env: __ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__main_135_145, x: i32, y: i64) -> i64 {
    return (y + 1);
}

fn callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__main_165_173_String_i32(__env: __ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__main_165_173, x: String, y: i32) -> i64 {
    return 1;
}

fn callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__main_188_193(__env: __ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__main_188_193) -> i64 {
    let __zv_callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__main_188_193_seed_i64 = __env.seed.clone();
    return (*__zv_callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__main_188_193_seed_i64.lock().unwrap() + 1);
}

fn callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__main_206_210_i64(__env: __ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__main_206_210, x: i64) -> i64 {
    let __zv_callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__main_206_210_i64_offset_i64 = __env.offset.clone();
    return (x + *__zv_callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__main_206_210_i64_offset_i64.lock().unwrap());
}

fn callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__main_220_224_i64(__env: __ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__main_220_224, x: i64) -> i64 {
    return (x + 3);
}

fn callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__main_263_269_i64(__env: __ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__main_263_269, x: i64) -> __ZincCallable_i64_to_i64 {
    let __zv_callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__main_263_269_i64_x_i64 = Arc::new(Mutex::new(x));
    return __ZincCallable_i64_to_i64::V0(__ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__main_263_269_i64_265_269 { x: __zv_callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__main_263_269_i64_x_i64.clone() });
}

fn callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__main_285_303_bool_i64(__env: __ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__main_285_303, flag: bool, value: i64) -> i64 {
    return if flag {
        (value + 1)
    } else {
        (value + 2)
    };
}

fn callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__main_330_334_i64(__env: __ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__main_330_334, x: i64) -> i64 {
    return (x * 5);
}

fn callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__main_344_352_i64_i64(__env: __ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__main_344_352, left: i64, right: i64) -> i64 {
    return (left - right);
}

fn callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__main_368_377_i64_i64(__env: __ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__main_368_377, x: i64, y: i64) -> i64 {
    return (x - y);
}

fn callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__main_392_402_i64_i32(__env: __ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__main_392_402, x: i64, y: i32) -> i64 {
    return (x * 4);
}

fn callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__main_83_89_i64(__env: __ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__main_83_89, x: i64) -> i64 {
    return (x + (1 * 2));
}

fn callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__make_chain_i64_47_55_i64(__env: __ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__make_chain_i64_47_55, y: i64) -> __ZincCallable_i64_to_i64 {
    let __zv_callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__make_chain_i64_47_55_i64_x_i64 = __env.x.clone();
    let __zv_callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__make_chain_i64_47_55_i64_y_i64 = Arc::new(Mutex::new(y));
    return __ZincCallable_i64_to_i64::V1(__ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__make_chain_i64_47_55_i64_49_55 { x: __zv_callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__make_chain_i64_47_55_i64_x_i64.clone(), y: __zv_callables_23_arrow_lambda_edges____lambda_callables_23_arrow_lambda_edges__make_chain_i64_47_55_i64_y_i64.clone() });
}

fn callables_23_arrow_lambda_edges__apply_twice_unknown_to_unknown_i64(f: __ZincCallable_i64_to_i64, x: i64) -> i64 {
    return f.call(f.call(x));
}

fn callables_23_arrow_lambda_edges__call_binary_unknown_i32_to_unknown_i64_i32(f: __ZincCallable_i64_i32_to_i64, left: i64, right: i32) -> i64 {
    return f.call(left, right);
}

fn callables_23_arrow_lambda_edges__choose_bool(flag: bool) -> __ZincCallable_i64_to_i64 {
    if flag {
        return __ZincCallable_i64_to_i64::V2(__ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__choose_bool_27_31 {});
    }
    return __ZincCallable_i64_to_i64::V3(__ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__choose_bool_34_38 {});
}

fn callables_23_arrow_lambda_edges__make_chain_i64(x: i64) -> __ZincCallable_i64_to_i64_to_i64 {
    let __zv_callables_23_arrow_lambda_edges__make_chain_i64_x_i64 = Arc::new(Mutex::new(x));
    return __ZincCallable_i64_to_i64_to_i64::V1(__ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__make_chain_i64_47_55 { x: __zv_callables_23_arrow_lambda_edges__make_chain_i64_x_i64.clone() });
}

fn main() {
    println!("{}", __ZincCallable_i64_to_i64::V7(__ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__main_83_89 {}).call(3));
    let use_i32_right: __ZincCallable_i64_i32_to_i64 = __ZincCallable_i64_i32_to_i64::V0(__ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__main_105_115 {});
    println!("{}", use_i32_right.call(5, (2i32) as i32));
    let use_i32_left: __ZincCallable_i32_i64_to_i64 = __ZincCallable_i32_i64_to_i64::V0(__ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__main_135_145 {});
    println!("{}", use_i32_left.call((3i32) as i32, 4));
    let ignore_first: __ZincCallable_String_i32_to_i64 = __ZincCallable_String_i32_to_i64::V0(__ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__main_165_173 {});
    println!("{}", ignore_first.call(String::from("wide"), (1i32) as i32));
    let __zv_callables_23_arrow_lambda_edges__main_seed_i64 = Arc::new(Mutex::new(9));
    let get = __ZincCallable_Unit_to_i64::V0(__ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__main_188_193 { seed: __zv_callables_23_arrow_lambda_edges__main_seed_i64.clone() });
    println!("{}", get.call());
    let __zv_callables_23_arrow_lambda_edges__main_offset_i64 = Arc::new(Mutex::new(6));
    println!("{}", __ZincCallable_i64_to_i64::V4(__ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__main_206_210 { offset: __zv_callables_23_arrow_lambda_edges__main_offset_i64.clone() }).call(4));
    println!("{}", callables_23_arrow_lambda_edges__apply_twice_unknown_to_unknown_i64(__ZincCallable_i64_to_i64::V5(__ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__main_220_224 {}), 1));
    let inc_or_step = callables_23_arrow_lambda_edges__choose_bool(false);
    println!("{}", inc_or_step.call(10));
    let nested = callables_23_arrow_lambda_edges__make_chain_i64(2);
    let plus_five = nested.call(3);
    println!("{}", plus_five.call(4));
    let curried = __ZincCallable_i64_to_i64_to_i64::V0(__ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__main_263_269 {});
    let times3 = curried.call(3);
    println!("{}", times3.call(4));
    let branch = __ZincCallable_bool_i64_to_i64::V0(__ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__main_285_303 {});
    println!("{}", branch.call(true, 4));
    println!("{}", branch.call(false, 4));
    let direct_slot: __ZincCallable_i64_to_i64 = __ZincCallable_i64_to_i64::V6(__ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__main_330_334 {});
    println!("{}", direct_slot.call(2));
    let named = __ZincCallable_i64_i64_to_i64::V0(__ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__main_344_352 {});
    println!("{}", named.call(10, 3));
    let trailing = __ZincCallable_i64_i64_to_i64::V1(__ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__main_368_377 {});
    println!("{}", trailing.call(10, 4));
    println!("{}", callables_23_arrow_lambda_edges__call_binary_unknown_i32_to_unknown_i64_i32(__ZincCallable_i64_i32_to_i64::V1(__ZincClosureEnv_callables_23_arrow_lambda_edges___lambda_callables_23_arrow_lambda_edges__main_392_402 {}), 3, 4i32));
}