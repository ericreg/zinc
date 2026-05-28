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
struct __ZincClosureEnv_functions_02_argument_spread___lambda_functions_02_argument_spread__main_251_270 {
}

#[derive(Clone)]
enum __ZincCallable_i64_i64_i64_to_i64 {
    Closed,
    V0(__ZincClosureEnv_functions_02_argument_spread___lambda_functions_02_argument_spread__main_251_270),
    V1,
}

impl Default for __ZincCallable_i64_i64_i64_to_i64 {
    fn default() -> Self {
        Self::Closed
    }
}

impl __ZincCallable_i64_i64_i64_to_i64 {
    fn call(&self, arg_0: i64, arg_1: i64, arg_2: i64) -> i64 {
        match self {
            Self::Closed => panic!("callable used after closed receive"),
            Self::V0(env) => functions_02_argument_spread____lambda_functions_02_argument_spread__main_251_270_i64_i64_i64(env.clone(), arg_0, arg_1, arg_2),
            Self::V1 => functions_02_argument_spread__combine_i64_i64_i64(arg_0, arg_1, arg_2),
        }
    }
}

#[derive(Clone, Default)]
struct __ZincAnonStruct_AnonStruct_a_i64_b_i64_c_i64_ignored_i64 {
    a: i64,
    b: i64,
    c: i64,
    ignored: i64,
}

struct functions_02_argument_spread__Args {
    pub a: i64,
    pub b: i64,
    pub c: i64,
    pub extra: i64,
}

impl Default for functions_02_argument_spread__Args {
    fn default() -> Self {
        Self { a: 0, b: 0, c: 0, extra: 0 }
    }
}

struct functions_02_argument_spread__PartialArgs {
    pub b: i64,
    pub c: i64,
}

impl Default for functions_02_argument_spread__PartialArgs {
    fn default() -> Self {
        Self { b: 0, c: 0 }
    }
}

struct functions_02_argument_spread__Tool {
    pub seed: i64,
}

impl Default for functions_02_argument_spread__Tool {
    fn default() -> Self {
        Self { seed: 0 }
    }
}

impl functions_02_argument_spread__Tool {
    fn add(&self, a: i64, b: i64, c: i64) -> i64 {
        return (((self.seed + a) + b) + c);
    }
    fn pack(a: i64, b: i64, c: i64) -> i64 {
        return (((a * 100) + (b * 10)) + c);
    }
}

fn functions_02_argument_spread____lambda_functions_02_argument_spread__main_251_270_i64_i64_i64(__env: __ZincClosureEnv_functions_02_argument_spread___lambda_functions_02_argument_spread__main_251_270, a: i64, b: i64, c: i64) -> i64 {
    return ((a + b) + c);
}

fn functions_02_argument_spread__combine_i64_i64_i64(a: i64, b: i64, c: i64) -> i64 {
    return (((a * 100) + (b * 10)) + c);
}

fn main() {
    let args = functions_02_argument_spread__Args { a: 1, b: 2, c: 3, extra: 99 };
    let partial = functions_02_argument_spread__PartialArgs { b: 7, c: 8 };
    let anon = __ZincAnonStruct_AnonStruct_a_i64_b_i64_c_i64_ignored_i64 { a: 4, b: 5, c: 6, ignored: 10 };
    println!("{}", functions_02_argument_spread__combine_i64_i64_i64(args.a, args.b, args.c));
    println!("{}", functions_02_argument_spread__combine_i64_i64_i64(9, args.b, args.c));
    println!("{}", functions_02_argument_spread__combine_i64_i64_i64(args.a, args.b, args.c));
    println!("{}", functions_02_argument_spread__combine_i64_i64_i64(4, partial.b, partial.c));
    println!("{}", functions_02_argument_spread__combine_i64_i64_i64(2, 3, 5));
    println!("{}", functions_02_argument_spread__combine_i64_i64_i64(anon.a, anon.b, anon.c));
    let f = __ZincCallable_i64_i64_i64_to_i64::V1;
    println!("{}", f.call(args.a, args.b, 6));
    let lambda = __ZincCallable_i64_i64_i64_to_i64::V0(__ZincClosureEnv_functions_02_argument_spread___lambda_functions_02_argument_spread__main_251_270 {});
    println!("{}", lambda.call(10, partial.b, partial.c));
    let tool = functions_02_argument_spread__Tool { seed: 100 };
    println!("{}", tool.add(1, partial.b, partial.c));
    println!("{}", functions_02_argument_spread__Tool::pack(2, partial.b, partial.c));
}