use zinc_internal::{Channel};

#[derive(Clone)]
enum __ZincCallable_i64_to_i64 {
    Closed,
    V0,
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
            Self::V0 => callables_21_channel_same_signature_mix__double_i64(arg_0),
            Self::V1 => callables_21_channel_same_signature_mix__inc_i64(arg_0),
        }
    }
}

fn callables_21_channel_same_signature_mix__double_i64(x: i64) -> i64 {
    return (x * 2);
}

fn callables_21_channel_same_signature_mix__inc_i64(x: i64) -> i64 {
    return (x + 1);
}

#[tokio::main]
async fn main() {
    let jobs = Channel::<__ZincCallable_i64_to_i64>::unbounded();
    jobs.send(__ZincCallable_i64_to_i64::V1).await;
    jobs.send(__ZincCallable_i64_to_i64::V0).await;
    let first = jobs.recv().await;
    let second = jobs.recv().await;
    println!("{}", first.call(2));
    println!("{}", second.call(2));
}