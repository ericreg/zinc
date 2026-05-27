const FUNCTIONS_01_NAMED_DEFAULTS__DEFAULT_COUNT: i32 = 7i32;

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
struct __ZincClosureEnv_functions_01_named_defaults___lambda_functions_01_named_defaults__main_414_427 {
}

#[derive(Clone)]
enum __ZincCallable_i64_to_i64 {
    Closed,
    V0(__ZincClosureEnv_functions_01_named_defaults___lambda_functions_01_named_defaults__main_414_427),
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
            Self::V0(env) => functions_01_named_defaults____lambda_functions_01_named_defaults__main_414_427_i64(env.clone(), arg_0),
            Self::V1 => functions_01_named_defaults__inc_i64(arg_0),
        }
    }
}

struct functions_01_named_defaults__Counter {
    pub value: i64,
}

impl Default for functions_01_named_defaults__Counter {
    fn default() -> Self {
        Self { value: 0 }
    }
}

impl functions_01_named_defaults__Counter {
    fn add(&mut self, amount: i64) {
        self.value += amount;
    }
    fn value_or(&self, extra: i64) -> i64 {
        return (self.value + extra);
    }
}

fn functions_01_named_defaults____lambda_functions_01_named_defaults__main_414_427_i64(__env: __ZincClosureEnv_functions_01_named_defaults___lambda_functions_01_named_defaults__main_414_427, x: i64) -> i64 {
    return (x * 2);
}

fn functions_01_named_defaults__add_i32_i32(x: i32, y: i32) -> i32 {
    return (x + y);
}

fn functions_01_named_defaults__blend_f64_i32(x: f64, y: i32) -> f64 {
    return (x + (y as f64));
}

fn functions_01_named_defaults__blend_i32_i32(x: i32, y: i32) -> i32 {
    return (x + y);
}

fn functions_01_named_defaults__inc_i64(x: i64) -> i64 {
    return (x + 1);
}

fn functions_01_named_defaults__numeric_default_f64_i64(x: f64, y: i64) -> f64 {
    return (x + (y as f64));
}

fn functions_01_named_defaults__numeric_default_i32_f64(x: i32, y: f64) -> f64 {
    return ((x as f64) + y);
}

fn functions_01_named_defaults__numeric_default_i64_f64(x: i64, y: f64) -> f64 {
    return ((x as f64) + y);
}

fn functions_01_named_defaults__order3_i64_i64_i64(a: i64, b: i64, c: i64) -> i64 {
    return (((a * 10000) + (b * 100)) + c);
}

async fn functions_01_named_defaults__send_value_Channel_i64(out: __ZincChannel<i64>, value: i64) {
    out.send(value).await;
}

fn functions_01_named_defaults__tag_String_i32(prefix: String, count: i32) -> String {
    return String::from(format!("{}:{}", prefix, count));
}

#[tokio::main]
async fn main() {
    let mut __zinc_spawn_handles = Vec::new();
    println!("{}", functions_01_named_defaults__add_i32_i32(10, 20));
    println!("{}", functions_01_named_defaults__add_i32_i32(2, 3));
    println!("{}", functions_01_named_defaults__add_i32_i32(5, 6));
    println!("{}", functions_01_named_defaults__add_i32_i32(4, 20));
    println!("{}", functions_01_named_defaults__add_i32_i32(10, 6));
    println!("{}", functions_01_named_defaults__add_i32_i32(7, 20));
    println!("{}", functions_01_named_defaults__blend_i32_i32(10, 5));
    println!("{}", functions_01_named_defaults__blend_f64_i32(3.5, 5));
    println!("{}", functions_01_named_defaults__blend_f64_i32(2.5, 4));
    println!("{}", functions_01_named_defaults__numeric_default_i32_f64(10, 2.5));
    println!("{}", functions_01_named_defaults__numeric_default_f64_i64(1.5, 4));
    println!("{}", functions_01_named_defaults__numeric_default_i64_f64(2, 2.5));
    println!("{}", functions_01_named_defaults__order3_i64_i64_i64(1, 20, 300));
    println!("{}", functions_01_named_defaults__order3_i64_i64_i64(1, 2, 300));
    println!("{}", functions_01_named_defaults__order3_i64_i64_i64(1, 2, 3));
    println!("{}", functions_01_named_defaults__order3_i64_i64_i64(1, 2, 3));
    println!("{}", functions_01_named_defaults__tag_String_i32(String::from("id"), FUNCTIONS_01_NAMED_DEFAULTS__DEFAULT_COUNT));
    println!("{}", functions_01_named_defaults__tag_String_i32(String::from("item"), FUNCTIONS_01_NAMED_DEFAULTS__DEFAULT_COUNT));
    println!("{}", functions_01_named_defaults__tag_String_i32(String::from("row"), 9));
    let ch = __ZincChannel::<i64>::unbounded();
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = ch.clone(); async move { functions_01_named_defaults__send_value_Channel_i64(__zinc_spawn_arg_0.clone(), 8).await; } }));
    println!("{}", ch.recv().await);
    let ch2 = __ZincChannel::<i64>::unbounded();
    __zinc_spawn_handles.push(tokio::spawn({ let __zinc_spawn_arg_0 = ch2.clone(); async move { functions_01_named_defaults__send_value_Channel_i64(__zinc_spawn_arg_0.clone(), 13).await; } }));
    println!("{}", ch2.recv().await);
    let lambda = __ZincCallable_i64_to_i64::V0(__ZincClosureEnv_functions_01_named_defaults___lambda_functions_01_named_defaults__main_414_427 {});
    println!("{}", lambda.call(4));
    println!("{}", lambda.call(6));
    let mut counter = functions_01_named_defaults__Counter { value: 0 };
    counter.add(1);
    counter.add(4);
    println!("{}", counter.value_or(5));
    counter.add(2);
    counter.add(3);
    println!("{}", counter.value_or(0));
    println!("{}", counter.value_or(1));
    let f = __ZincCallable_i64_to_i64::V1;
    println!("{}", f.call(9));
    println!("{}", f.call(3));
    println!("{}", f.call(1));
    while let Some(__zinc_spawn_handle) = __zinc_spawn_handles.pop() {
        __zinc_spawn_handle.await.unwrap();
    }
}