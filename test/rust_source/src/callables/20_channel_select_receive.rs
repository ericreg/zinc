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
            Self::V0 => callables_20_channel_select_receive__inc_i64(arg_0),
        }
    }
}

fn callables_20_channel_select_receive__inc_i64(x: i64) -> i64 {
    return (x + 1);
}

#[tokio::main]
async fn main() {
    let jobs = Channel::<__ZincCallable_i64_to_i64>::unbounded();
    jobs.send(__ZincCallable_i64_to_i64::V0).await;
    tokio::select! {
        __zinc_select_value_0_0 = async { jobs.recv_option().await } => {
            let f = match __zinc_select_value_0_0 { Some(value) => value, None => panic!("select receive on closed channel") };
            println!("{}", f.call(6));
        },
    }
}