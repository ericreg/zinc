use std::cmp::max;
use zinc_internal::{Channel};

struct functions_04_ufcs__Counter {
    pub value: i64,
}

impl Default for functions_04_ufcs__Counter {
    fn default() -> Self {
        Self { value: 0 }
    }
}

impl functions_04_ufcs__Counter {
    fn reset(&mut self) {
        self.value = 5;
    }
}

struct functions_04_ufcs__Extra {
    pub b: i64,
    pub c: i64,
}

impl Default for functions_04_ufcs__Extra {
    fn default() -> Self {
        Self { b: 0, c: 0 }
    }
}

fn functions_04_ufcs__combine_i64_i64_i64_i64(x: i64, a: i64, b: i64, c: i64) -> i64 {
    return ((((x * 1000) + (a * 100)) + (b * 10)) + c);
}

async fn functions_04_ufcs__send_next_i64_Channel(value: i64, done: Channel<i64>) {
    done.send((value + 1)).await;
}

fn functions_04_ufcs__twice_i64(x: i64) -> i64 {
    return (x + x);
}

fn modules__lib_math__add_i64_i64(a: i64, b: i64) -> i64 {
    return (a + b);
}

#[tokio::main]
async fn main() {
    let mut __zinc_spawn_handles = Vec::new();
    let n = 2;
    let extra = functions_04_ufcs__Extra { b: 3, c: 4 };
    println!("{}", functions_04_ufcs__combine_i64_i64_i64_i64(n, 1, 10, 100));
    println!("{}", functions_04_ufcs__combine_i64_i64_i64_i64(n, 1, 2, 100));
    println!("{}", functions_04_ufcs__combine_i64_i64_i64_i64(n, 1, extra.b, extra.c));
    println!("{}", functions_04_ufcs__twice_i64(4));
    println!("{}", modules__lib_math__add_i64_i64(10, 5));
    println!("{}", max(7, 11));
    let mut counter = functions_04_ufcs__Counter { value: 0 };
    counter.reset();
    println!("{}", counter.value);
    let done = Channel::<i64>::unbounded();
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_1 = done.clone(); async move { functions_04_ufcs__send_next_i64_Channel(40, __zinc_spawn_arg_1.clone()).await; } }));
    println!("{}", done.recv().await);
    while let Some(__zinc_spawn_handle) = __zinc_spawn_handles.pop() {
        __zinc_spawn_handle.await.unwrap();
    }
}