use zinc_internal::{__ZincChannel, __ZincContext};

#[derive(Clone)]
enum __ZincCallable_Unit_to_Unit {
    Closed,
    V0(__ZincContext),
}

impl Default for __ZincCallable_Unit_to_Unit {
    fn default() -> Self {
        Self::Closed
    }
}

impl __ZincCallable_Unit_to_Unit {
    fn call(&self, ) {
        match self {
            Self::Closed => panic!("callable used after closed receive"),
            Self::V0(ctx) => { ctx.cancel(); }
        }
    }
}

async fn concurrency_select_09_context_spawn_cancel__wait_for_cancel___ZincContext_Channel(ctx: __ZincContext, output: __ZincChannel<i64>) {
    tokio::select! {
        __zinc_select_value_0_0 = async { ctx.done().recv_option().await } => {
            output.send(1).await;
            output.close();
        },
    }
}

#[tokio::main]
async fn main() {
    let mut __zinc_spawn_handles = Vec::new();
    let root = __ZincContext::background();
    let (child, cancel) = {
        let __zinc_parent_ctx = root.clone();
        let __zinc_child_ctx = __ZincContext::background();
        let __zinc_child_for_task = __zinc_child_ctx.clone();
        tokio::spawn(async move {
            let _ = __zinc_parent_ctx.done().recv_option().await;
            __zinc_child_for_task.cancel();
        });
        (__zinc_child_ctx.clone(), __ZincCallable_Unit_to_Unit::V0(__zinc_child_ctx))
    };
    let output = __ZincChannel::<i64>::unbounded();
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_1 = output.clone(); async move { concurrency_select_09_context_spawn_cancel__wait_for_cancel___ZincContext_Channel(child, __zinc_spawn_arg_1.clone()).await; } }));
    cancel.call();
    println!("{}", output.recv().await);
    while let Some(__zinc_spawn_handle) = __zinc_spawn_handles.pop() {
        __zinc_spawn_handle.await.unwrap();
    }
}