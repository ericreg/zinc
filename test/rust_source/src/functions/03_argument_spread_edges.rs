struct functions_03_argument_spread_edges__AB {
    pub a: i64,
    pub b: i64,
}

impl Default for functions_03_argument_spread_edges__AB {
    fn default() -> Self {
        Self { a: 0, b: 0 }
    }
}

struct functions_03_argument_spread_edges__Args {
    pub a: i64,
    pub b: i64,
    pub c: i64,
    pub extra: i64,
}

impl Default for functions_03_argument_spread_edges__Args {
    fn default() -> Self {
        Self { a: 0, b: 0, c: 0, extra: 0 }
    }
}

struct functions_03_argument_spread_edges__BC {
    pub b: i64,
    pub c: i64,
}

impl Default for functions_03_argument_spread_edges__BC {
    fn default() -> Self {
        Self { b: 0, c: 0 }
    }
}

struct functions_03_argument_spread_edges__BadA {
    pub a: String,
    pub b: i64,
    pub c: i64,
}

impl Default for functions_03_argument_spread_edges__BadA {
    fn default() -> Self {
        Self { a: String::new(), b: 0, c: 0 }
    }
}

struct functions_03_argument_spread_edges__Holder {
    pub nested: functions_03_argument_spread_edges__Args,
}

impl Default for functions_03_argument_spread_edges__Holder {
    fn default() -> Self {
        Self { nested: Default::default() }
    }
}

struct functions_03_argument_spread_edges__OnlyB {
    pub b: i64,
}

impl Default for functions_03_argument_spread_edges__OnlyB {
    fn default() -> Self {
        Self { b: 0 }
    }
}

fn functions_03_argument_spread_edges__ignored_args() -> functions_03_argument_spread_edges__Args {
    println!("ignore args");
    return functions_03_argument_spread_edges__Args { a: 9, b: 9, c: 9, extra: 99 };
}

fn functions_03_argument_spread_edges__noisy_args() -> functions_03_argument_spread_edges__Args {
    println!("make args");
    return functions_03_argument_spread_edges__Args { a: 3, b: 2, c: 1, extra: 99 };
}

fn functions_03_argument_spread_edges__pack_i64_i64_i64(a: i64, b: i64, c: i64) -> i64 {
    return (((a * 100) + (b * 10)) + c);
}

fn main() {
    let left = functions_03_argument_spread_edges__AB { a: 1, b: 2 };
    let right = functions_03_argument_spread_edges__BC { b: 7, c: 8 };
    let only_b = functions_03_argument_spread_edges__OnlyB { b: 4 };
    let holder = functions_03_argument_spread_edges__Holder { nested: functions_03_argument_spread_edges__Args { a: 6, b: 5, c: 4, extra: 0 } };
    let bad = functions_03_argument_spread_edges__BadA { a: String::from("bad"), b: 8, c: 9 };
    println!("{}", functions_03_argument_spread_edges__pack_i64_i64_i64(left.a, right.b, right.c));
    println!("{}", functions_03_argument_spread_edges__pack_i64_i64_i64(left.a, left.b, 5));
    println!("{}", functions_03_argument_spread_edges__pack_i64_i64_i64(3, only_b.b, 9));
    println!("{}", functions_03_argument_spread_edges__pack_i64_i64_i64(holder.nested.a, holder.nested.b, holder.nested.c));
    println!("{}", functions_03_argument_spread_edges__pack_i64_i64_i64(7, bad.b, bad.c));
    println!("{}", {
        let __zinc_arg_spread_293_295 = functions_03_argument_spread_edges__noisy_args();
        functions_03_argument_spread_edges__pack_i64_i64_i64(__zinc_arg_spread_293_295.a, __zinc_arg_spread_293_295.b, __zinc_arg_spread_293_295.c)
    });
    println!("{}", functions_03_argument_spread_edges__pack_i64_i64_i64(1, 2, 3));
    println!("{}", {
        let __zinc_arg_spread_337_339 = functions_03_argument_spread_edges__noisy_args();
        functions_03_argument_spread_edges__pack_i64_i64_i64(__zinc_arg_spread_337_339.a, __zinc_arg_spread_337_339.b, __zinc_arg_spread_337_339.c)
    });
}