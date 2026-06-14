const FUNCTIONS_05_UFCS_EDGE_CASES__BASE: i64 = 4;

#[derive(Clone)]
struct __ZincClosureEnv_functions_05_ufcs_edge_cases___lambda_functions_05_ufcs_edge_cases__main_177_181 {
}

#[derive(Clone)]
struct __ZincClosureEnv_functions_05_ufcs_edge_cases___lexical_functions_05_ufcs_edge_cases__main_local_add_149_165 {
}

#[derive(Clone)]
enum __ZincCallable_i64_to_i64 {
    Closed,
    V0(__ZincClosureEnv_functions_05_ufcs_edge_cases___lambda_functions_05_ufcs_edge_cases__main_177_181),
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
            Self::V0(env) => functions_05_ufcs_edge_cases____lambda_functions_05_ufcs_edge_cases__main_177_181_i64(env.clone(), arg_0),
        }
    }
}

#[derive(Clone, Default)]
struct __ZincAnonStruct_AnonStruct_x_i64_y_i64 {
    x: i64,
    y: i64,
}

fn functions_05_ufcs_edge_cases____lambda_functions_05_ufcs_edge_cases__main_177_181_i64(__env: __ZincClosureEnv_functions_05_ufcs_edge_cases___lambda_functions_05_ufcs_edge_cases__main_177_181, x: i64) -> i64 {
    return (x + 1);
}

fn functions_05_ufcs_edge_cases____lexical_functions_05_ufcs_edge_cases__main_local_add_149_165_i64_i64(__env: __ZincClosureEnv_functions_05_ufcs_edge_cases___lexical_functions_05_ufcs_edge_cases__main_local_add_149_165, value: i64, inc: i64) -> i64 {
    return ((value + inc) + 100);
}

fn functions_05_ufcs_edge_cases__apply_unknown_to_unknown_i64(f: __ZincCallable_i64_to_i64, x: i64) -> i64 {
    return f.call(x);
}

fn functions_05_ufcs_edge_cases__describe_AnonStruct_x_i64_y_i64(point: __ZincAnonStruct_AnonStruct_x_i64_y_i64) -> i64 {
    return (point.x + point.y);
}

fn functions_05_ufcs_edge_cases__make() -> i64 {
    return 6;
}

fn functions_05_ufcs_edge_cases__scale_i64_i64(value: i64, by: i64) -> i64 {
    return (value * by);
}

fn modules__lib_math__add_i64_i64(a: i64, b: i64) -> i64 {
    return (a + b);
}

fn main() {
    println!("{}", functions_05_ufcs_edge_cases__scale_i64_i64(((FUNCTIONS_05_UFCS_EDGE_CASES__BASE + 1)), 3));
    println!("{}", functions_05_ufcs_edge_cases__scale_i64_i64(functions_05_ufcs_edge_cases__make(), 4));
    println!("{}", modules__lib_math__add_i64_i64(FUNCTIONS_05_UFCS_EDGE_CASES__BASE, 8));
    println!("{}", functions_05_ufcs_edge_cases____lexical_functions_05_ufcs_edge_cases__main_local_add_149_165_i64_i64(__ZincClosureEnv_functions_05_ufcs_edge_cases___lexical_functions_05_ufcs_edge_cases__main_local_add_149_165 {}, 5, 6));
    let inc = __ZincCallable_i64_to_i64::V0(__ZincClosureEnv_functions_05_ufcs_edge_cases___lambda_functions_05_ufcs_edge_cases__main_177_181 {});
    println!("{}", functions_05_ufcs_edge_cases__apply_unknown_to_unknown_i64(inc.clone(), 9));
    println!("{}", inc.call(9));
    let values = vec![1, 2, 3];
    println!("{}", (values.len() as i64));
    let point = __ZincAnonStruct_AnonStruct_x_i64_y_i64 { x: 2, y: 8 };
    println!("{}", functions_05_ufcs_edge_cases__describe_AnonStruct_x_i64_y_i64(point));
}