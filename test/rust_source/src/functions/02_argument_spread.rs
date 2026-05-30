#[derive(Clone)]
struct __ZincClosureEnv_functions_02_argument_spread___lambda_functions_02_argument_spread__main_251_270 {
}

#[derive(Clone)]
enum __ZincCallable_i64_i64_i64_to_i64 {
    Closed,
    V0(__ZincClosureEnv_functions_02_argument_spread___lambda_functions_02_argument_spread__main_251_270),
    V1,
}

impl Default for __ZincCallable_i64_i64_i64_to_i64 {
    fn default() -> Self {
        Self::Closed
    }
}

impl __ZincCallable_i64_i64_i64_to_i64 {
    fn call(&self, arg_0: i64, arg_1: i64, arg_2: i64) -> i64 {
        match self {
            Self::Closed => panic!("callable used after closed receive"),
            Self::V0(env) => functions_02_argument_spread____lambda_functions_02_argument_spread__main_251_270_i64_i64_i64(env.clone(), arg_0, arg_1, arg_2),
            Self::V1 => functions_02_argument_spread__combine_i64_i64_i64(arg_0, arg_1, arg_2),
        }
    }
}

#[derive(Clone, Default)]
struct __ZincAnonStruct_AnonStruct_a_i64_b_i64_c_i64_ignored_i64 {
    a: i64,
    b: i64,
    c: i64,
    ignored: i64,
}

struct functions_02_argument_spread__Args {
    pub a: i64,
    pub b: i64,
    pub c: i64,
    pub extra: i64,
}

impl Default for functions_02_argument_spread__Args {
    fn default() -> Self {
        Self { a: 0, b: 0, c: 0, extra: 0 }
    }
}

struct functions_02_argument_spread__PartialArgs {
    pub b: i64,
    pub c: i64,
}

impl Default for functions_02_argument_spread__PartialArgs {
    fn default() -> Self {
        Self { b: 0, c: 0 }
    }
}

struct functions_02_argument_spread__Tool {
    pub seed: i64,
}

impl Default for functions_02_argument_spread__Tool {
    fn default() -> Self {
        Self { seed: 0 }
    }
}

impl functions_02_argument_spread__Tool {
    fn add(&self, a: i64, b: i64, c: i64) -> i64 {
        return (((self.seed + a) + b) + c);
    }
    fn pack(a: i64, b: i64, c: i64) -> i64 {
        return (((a * 100) + (b * 10)) + c);
    }
}

fn functions_02_argument_spread____lambda_functions_02_argument_spread__main_251_270_i64_i64_i64(__env: __ZincClosureEnv_functions_02_argument_spread___lambda_functions_02_argument_spread__main_251_270, a: i64, b: i64, c: i64) -> i64 {
    return ((a + b) + c);
}

fn functions_02_argument_spread__combine_i64_i64_i64(a: i64, b: i64, c: i64) -> i64 {
    return (((a * 100) + (b * 10)) + c);
}

fn main() {
    let args = functions_02_argument_spread__Args { a: 1, b: 2, c: 3, extra: 99 };
    let partial = functions_02_argument_spread__PartialArgs { b: 7, c: 8 };
    let anon = __ZincAnonStruct_AnonStruct_a_i64_b_i64_c_i64_ignored_i64 { a: 4, b: 5, c: 6, ignored: 10 };
    println!("{}", functions_02_argument_spread__combine_i64_i64_i64(args.a, args.b, args.c));
    println!("{}", functions_02_argument_spread__combine_i64_i64_i64(9, args.b, args.c));
    println!("{}", functions_02_argument_spread__combine_i64_i64_i64(args.a, args.b, args.c));
    println!("{}", functions_02_argument_spread__combine_i64_i64_i64(4, partial.b, partial.c));
    println!("{}", functions_02_argument_spread__combine_i64_i64_i64(2, 3, 5));
    println!("{}", functions_02_argument_spread__combine_i64_i64_i64(anon.a, anon.b, anon.c));
    let f = __ZincCallable_i64_i64_i64_to_i64::V1;
    println!("{}", f.call(args.a, args.b, 6));
    let lambda = __ZincCallable_i64_i64_i64_to_i64::V0(__ZincClosureEnv_functions_02_argument_spread___lambda_functions_02_argument_spread__main_251_270 {});
    println!("{}", lambda.call(10, partial.b, partial.c));
    let tool = functions_02_argument_spread__Tool { seed: 100 };
    println!("{}", tool.add(1, partial.b, partial.c));
    println!("{}", functions_02_argument_spread__Tool::pack(2, partial.b, partial.c));
}