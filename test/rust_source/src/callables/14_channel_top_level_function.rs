use zinc_internal::{__ZincChannel};

#[derive(Clone)]
enum __ZincCallable_i64_to_i64 {
    Closed,
    V0,
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
            Self::V0 => callables_14_channel_top_level_function__inc_i64(arg_0),
        }
    }
}

fn callables_14_channel_top_level_function__inc_i64(x: i64) -> i64 {
    return (x + 1);
}

#[tokio::main]
async fn main() {
    let jobs = __ZincChannel::<__ZincCallable_i64_to_i64>::unbounded();
    jobs.send(__ZincCallable_i64_to_i64::V0).await;
    let f = jobs.recv().await;
    println!("{}", f.call(3));
}