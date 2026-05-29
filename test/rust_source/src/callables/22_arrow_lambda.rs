use std::sync::{Arc, Mutex};

enum __ZincTryRecv<T> {
    Value(T),
    Empty,
    Closed,
}

enum __ZincTrySend<T> {
    Sent,
    Full(T),
    Closed(T),
}

enum __ZincChannelSender<T> {
    Bounded(tokio::sync::mpsc::Sender<T>),
    Unbounded(tokio::sync::mpsc::UnboundedSender<T>),
}

enum __ZincChannelReceiver<T> {
    Bounded(tokio::sync::mpsc::Receiver<T>),
    Unbounded(tokio::sync::mpsc::UnboundedReceiver<T>),
}

impl<T> __ZincChannelReceiver<T> {
    async fn recv(&mut self) -> Option<T> {
        match self {
            Self::Bounded(receiver) => receiver.recv().await,
            Self::Unbounded(receiver) => receiver.recv().await,
        }
    }

    fn try_recv(&mut self) -> __ZincTryRecv<T> {
        match self {
            Self::Bounded(receiver) => match receiver.try_recv() {
                Ok(value) => __ZincTryRecv::Value(value),
                Err(tokio::sync::mpsc::error::TryRecvError::Empty) => __ZincTryRecv::Empty,
                Err(tokio::sync::mpsc::error::TryRecvError::Disconnected) => __ZincTryRecv::Closed,
            },
            Self::Unbounded(receiver) => match receiver.try_recv() {
                Ok(value) => __ZincTryRecv::Value(value),
                Err(tokio::sync::mpsc::error::TryRecvError::Empty) => __ZincTryRecv::Empty,
                Err(tokio::sync::mpsc::error::TryRecvError::Disconnected) => __ZincTryRecv::Closed,
            },
        }
    }
}

impl<T> Clone for __ZincChannelSender<T> {
    fn clone(&self) -> Self {
        match self {
            Self::Bounded(sender) => Self::Bounded(sender.clone()),
            Self::Unbounded(sender) => Self::Unbounded(sender.clone()),
        }
    }
}

struct __ZincChannel<T> {
    sender: __ZincChannelSender<T>,
    receiver: std::sync::Arc<tokio::sync::Mutex<__ZincChannelReceiver<T>>>,
    closed: std::sync::Arc<std::sync::atomic::AtomicBool>,
    close_notify: std::sync::Arc<tokio::sync::Notify>,
}

impl<T> Clone for __ZincChannel<T> {
    fn clone(&self) -> Self {
        Self {
            sender: self.sender.clone(),
            receiver: self.receiver.clone(),
            closed: self.closed.clone(),
            close_notify: self.close_notify.clone(),
        }
    }
}

impl<T: Send + 'static> __ZincChannel<T> {
    fn bounded(capacity: i64) -> Self {
        let (sender, receiver) = tokio::sync::mpsc::channel(capacity as usize);
        Self {
            sender: __ZincChannelSender::Bounded(sender),
            receiver: std::sync::Arc::new(tokio::sync::Mutex::new(__ZincChannelReceiver::Bounded(receiver))),
            closed: std::sync::Arc::new(std::sync::atomic::AtomicBool::new(false)),
            close_notify: std::sync::Arc::new(tokio::sync::Notify::new()),
        }
    }

    fn unbounded() -> Self {
        let (sender, receiver) = tokio::sync::mpsc::unbounded_channel();
        Self {
            sender: __ZincChannelSender::Unbounded(sender),
            receiver: std::sync::Arc::new(tokio::sync::Mutex::new(__ZincChannelReceiver::Unbounded(receiver))),
            closed: std::sync::Arc::new(std::sync::atomic::AtomicBool::new(false)),
            close_notify: std::sync::Arc::new(tokio::sync::Notify::new()),
        }
    }

    async fn send(&self, value: T) {
        if self.closed.load(std::sync::atomic::Ordering::SeqCst) {
            panic!("send on closed channel");
        }
        match &self.sender {
            __ZincChannelSender::Bounded(sender) => {
                if let Err(_) = sender.send(value).await {
                    panic!("send on closed channel");
                }
            },
            __ZincChannelSender::Unbounded(sender) => {
                if let Err(_) = sender.send(value) {
                    panic!("send on closed channel");
                }
            },
        }
    }

    fn try_send(&self, value: T) -> __ZincTrySend<T> {
        if self.closed.load(std::sync::atomic::Ordering::SeqCst) {
            return __ZincTrySend::Closed(value);
        }
        match &self.sender {
            __ZincChannelSender::Bounded(sender) => match sender.try_send(value) {
                Ok(()) => __ZincTrySend::Sent,
                Err(tokio::sync::mpsc::error::TrySendError::Full(value)) => __ZincTrySend::Full(value),
                Err(tokio::sync::mpsc::error::TrySendError::Closed(value)) => __ZincTrySend::Closed(value),
            },
            __ZincChannelSender::Unbounded(sender) => match sender.send(value) {
                Ok(()) => __ZincTrySend::Sent,
                Err(err) => __ZincTrySend::Closed(err.0),
            },
        }
    }

    fn close(&self) {
        if self.closed.swap(true, std::sync::atomic::Ordering::SeqCst) {
            panic!("double close");
        }
        self.close_notify.notify_waiters();
    }

    async fn recv_option(&self) -> Option<T> {
        loop {
            match self.receiver.clone().try_lock_owned() {
                Ok(mut receiver) => match receiver.try_recv() {
                    __ZincTryRecv::Value(value) => return Some(value),
                    __ZincTryRecv::Closed => return None,
                    __ZincTryRecv::Empty => {
                        if self.closed.load(std::sync::atomic::Ordering::SeqCst) {
                            return None;
                        }
                        let notified = self.close_notify.notified();
                        drop(receiver);
                        tokio::select! {
                            value = async {
                                let mut receiver = self.receiver.clone().lock_owned().await;
                                receiver.recv().await
                            } => return value,
                            _ = notified => continue,
                        }
                    },
                },
                Err(_) => tokio::task::yield_now().await,
            }
        }
    }

    async fn recv(&self) -> T {
        match self.recv_option().await {
            Some(value) => value,
            None => panic!("receive on closed channel"),
        }
    }

    fn try_recv(&self) -> __ZincTryRecv<T> {
        match self.receiver.clone().try_lock_owned() {
            Ok(mut receiver) => match receiver.try_recv() {
                __ZincTryRecv::Empty if self.closed.load(std::sync::atomic::Ordering::SeqCst) => __ZincTryRecv::Closed,
                result => result,
            },
            Err(_) => __ZincTryRecv::Empty,
        }
    }
}

#[derive(Clone)]
struct __ZincContext {
    done: __ZincChannel<bool>,
}

impl Default for __ZincContext {
    fn default() -> Self {
        Self::background()
    }
}

impl __ZincContext {
    fn background() -> Self {
        Self { done: __ZincChannel::unbounded() }
    }

    fn done(&self) -> __ZincChannel<bool> {
        self.done.clone()
    }

    fn cancel(&self) {
        self.done.close();
    }
}

#[derive(Clone)]
struct __ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__main_90_96_i64_92_96 {
    x: Arc<Mutex<i64>>,
}

#[derive(Clone)]
struct __ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_118_122 {
}

#[derive(Clone)]
struct __ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_128_132 {
}

#[derive(Clone)]
struct __ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_157_160 {
}

#[derive(Clone)]
struct __ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_168_172 {
}

#[derive(Clone)]
struct __ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_36_40 {
}

#[derive(Clone)]
struct __ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_55_65 {
}

#[derive(Clone)]
struct __ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_90_96 {
}

#[derive(Clone)]
struct __ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__make_offset_i64_21_25 {
    base: Arc<Mutex<i64>>,
}

#[derive(Clone)]
enum __ZincCallable_Unit_to_i64 {
    Closed,
    V0(__ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_157_160),
}

impl Default for __ZincCallable_Unit_to_i64 {
    fn default() -> Self {
        Self::Closed
    }
}

impl __ZincCallable_Unit_to_i64 {
    fn call(&self, ) -> i64 {
        match self {
            Self::Closed => panic!("callable used after closed receive"),
            Self::V0(env) => callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__main_157_160(env.clone()),
        }
    }
}

#[derive(Clone)]
enum __ZincCallable_i64_i32_to_i64 {
    Closed,
    V0(__ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_55_65),
}

impl Default for __ZincCallable_i64_i32_to_i64 {
    fn default() -> Self {
        Self::Closed
    }
}

impl __ZincCallable_i64_i32_to_i64 {
    fn call(&self, arg_0: i64, arg_1: i32) -> i64 {
        match self {
            Self::Closed => panic!("callable used after closed receive"),
            Self::V0(env) => callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__main_55_65_i64_i32(env.clone(), arg_0, arg_1),
        }
    }
}

#[derive(Clone)]
enum __ZincCallable_i64_to_i64 {
    Closed,
    V0(__ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__main_90_96_i64_92_96),
    V1(__ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_118_122),
    V2(__ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_128_132),
    V3(__ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_168_172),
    V4(__ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_36_40),
    V5(__ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__make_offset_i64_21_25),
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
            Self::V0(env) => callables_22_arrow_lambda____lambda_callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__main_90_96_i64_92_96_i64(env.clone(), arg_0),
            Self::V1(env) => callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__main_118_122_i64(env.clone(), arg_0),
            Self::V2(env) => callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__main_128_132_i64(env.clone(), arg_0),
            Self::V3(env) => callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__main_168_172_i64(env.clone(), arg_0),
            Self::V4(env) => callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__main_36_40_i64(env.clone(), arg_0),
            Self::V5(env) => callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__make_offset_i64_21_25_i64(env.clone(), arg_0),
        }
    }
}

#[derive(Clone)]
enum __ZincCallable_i64_to_i64_to_i64 {
    Closed,
    V0(__ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_90_96),
}

impl Default for __ZincCallable_i64_to_i64_to_i64 {
    fn default() -> Self {
        Self::Closed
    }
}

impl __ZincCallable_i64_to_i64_to_i64 {
    fn call(&self, arg_0: i64) -> __ZincCallable_i64_to_i64 {
        match self {
            Self::Closed => panic!("callable used after closed receive"),
            Self::V0(env) => callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__main_90_96_i64(env.clone(), arg_0),
        }
    }
}

fn callables_22_arrow_lambda____lambda_callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__main_90_96_i64_92_96_i64(__env: __ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__main_90_96_i64_92_96, y: i64) -> i64 {
    let __zv_callables_22_arrow_lambda____lambda_callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__main_90_96_i64_92_96_i64_x_i64 = __env.x.clone();
    return (*__zv_callables_22_arrow_lambda____lambda_callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__main_90_96_i64_92_96_i64_x_i64.lock().unwrap() + y);
}

fn callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__main_118_122_i64(__env: __ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_118_122, x: i64) -> i64 {
    return (x + 1);
}

fn callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__main_128_132_i64(__env: __ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_128_132, x: i64) -> i64 {
    return (x * 2);
}

fn callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__main_157_160(__env: __ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_157_160) -> i64 {
    return 42;
}

fn callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__main_168_172_i64(__env: __ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_168_172, x: i64) -> i64 {
    return (x * 2);
}

fn callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__main_36_40_i64(__env: __ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_36_40, x: i64) -> i64 {
    return (x + 1);
}

fn callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__main_55_65_i64_i32(__env: __ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_55_65, x: i64, y: i32) -> i64 {
    return (x + 1);
}

fn callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__main_90_96_i64(__env: __ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_90_96, x: i64) -> __ZincCallable_i64_to_i64 {
    let __zv_callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__main_90_96_i64_x_i64 = Arc::new(Mutex::new(x));
    return __ZincCallable_i64_to_i64::V0(__ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__main_90_96_i64_92_96 { x: __zv_callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__main_90_96_i64_x_i64.clone() });
}

fn callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__make_offset_i64_21_25_i64(__env: __ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__make_offset_i64_21_25, x: i64) -> i64 {
    let __zv_callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__make_offset_i64_21_25_i64_base_i64 = __env.base.clone();
    return (x + *__zv_callables_22_arrow_lambda____lambda_callables_22_arrow_lambda__make_offset_i64_21_25_i64_base_i64.lock().unwrap());
}

fn callables_22_arrow_lambda__apply_unknown_to_unknown_i64(f: __ZincCallable_i64_to_i64, x: i64) -> i64 {
    return f.call(x);
}

fn callables_22_arrow_lambda__make_offset_i64(base: i64) -> __ZincCallable_i64_to_i64 {
    let __zv_callables_22_arrow_lambda__make_offset_i64_base_i64 = Arc::new(Mutex::new(base));
    return __ZincCallable_i64_to_i64::V5(__ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__make_offset_i64_21_25 { base: __zv_callables_22_arrow_lambda__make_offset_i64_base_i64.clone() });
}

fn main() {
    println!("{}", callables_22_arrow_lambda__apply_unknown_to_unknown_i64(__ZincCallable_i64_to_i64::V4(__ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_36_40 {}), 4));
    let partial: __ZincCallable_i64_i32_to_i64 = __ZincCallable_i64_i32_to_i64::V0(__ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_55_65 {});
    println!("{}", partial.call(5, (2i32) as i32));
    let add10 = callables_22_arrow_lambda__make_offset_i64(10);
    println!("{}", add10.call(5));
    let maker = __ZincCallable_i64_to_i64_to_i64::V0(__ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_90_96 {});
    let add7 = maker.call(7);
    println!("{}", add7.call(8));
    let mut ops = vec![];
    ops.push(__ZincCallable_i64_to_i64::V1(__ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_118_122 {}));
    ops.push(__ZincCallable_i64_to_i64::V2(__ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_128_132 {}));
    println!("{}", ops[0].call(3));
    println!("{}", ops[1].call(3));
    println!("{}", __ZincCallable_Unit_to_i64::V0(__ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_157_160 {}).call());
    println!("{}", __ZincCallable_i64_to_i64::V3(__ZincClosureEnv_callables_22_arrow_lambda___lambda_callables_22_arrow_lambda__main_168_172 {}).call(5));
}