use zinc_internal::{Channel};

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
            Self::V0 => callables_17_channel_helper_param__inc_i64(arg_0),
        }
    }
}

fn callables_17_channel_helper_param__inc_i64(x: i64) -> i64 {
    return (x + 1);
}

async fn callables_17_channel_helper_param__publish_Channel(out: Channel<__ZincCallable_i64_to_i64>) {
    out.send(__ZincCallable_i64_to_i64::V0).await;
}

async fn callables_17_channel_helper_param__publish_Channel_i64_to_i64(out: Channel<__ZincCallable_i64_to_i64>) {
    out.send(__ZincCallable_i64_to_i64::V0).await;
}

async fn callables_17_channel_helper_param__publish_Channel_i64_to_unknown(out: Channel<__ZincCallable_i64_to_i64>) {
    out.send(__ZincCallable_i64_to_i64::V0).await;
}

async fn callables_17_channel_helper_param__publish_Channel_unknown_to_unknown(out: Channel<__ZincCallable_i64_to_i64>) {
    out.send(__ZincCallable_i64_to_i64::V0).await;
}

#[tokio::main]
async fn main() {
    let jobs = Channel::<__ZincCallable_i64_to_i64>::unbounded();
    callables_17_channel_helper_param__publish_Channel_i64_to_i64(jobs.clone()).await;
    let f = jobs.recv().await;
    println!("{}", f.call(4));
}