use zinc_internal::{__ZincContext};

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

#[tokio::main]
async fn main() {
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
    cancel.call();
    tokio::select! {
        __zinc_select_value_0_0 = async { child.done().recv_option().await } => {
            println!("done");
        },
    }
}