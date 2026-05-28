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

struct functions_03_argument_spread_edges__AB {
    pub a: i64,
    pub b: i64,
}

impl Default for functions_03_argument_spread_edges__AB {
    fn default() -> Self {
        Self { a: 0, b: 0 }
    }
}

struct functions_03_argument_spread_edges__Args {
    pub a: i64,
    pub b: i64,
    pub c: i64,
    pub extra: i64,
}

impl Default for functions_03_argument_spread_edges__Args {
    fn default() -> Self {
        Self { a: 0, b: 0, c: 0, extra: 0 }
    }
}

struct functions_03_argument_spread_edges__BC {
    pub b: i64,
    pub c: i64,
}

impl Default for functions_03_argument_spread_edges__BC {
    fn default() -> Self {
        Self { b: 0, c: 0 }
    }
}

struct functions_03_argument_spread_edges__BadA {
    pub a: String,
    pub b: i64,
    pub c: i64,
}

impl Default for functions_03_argument_spread_edges__BadA {
    fn default() -> Self {
        Self { a: String::new(), b: 0, c: 0 }
    }
}

struct functions_03_argument_spread_edges__Holder {
    pub nested: functions_03_argument_spread_edges__Args,
}

impl Default for functions_03_argument_spread_edges__Holder {
    fn default() -> Self {
        Self { nested: Default::default() }
    }
}

struct functions_03_argument_spread_edges__OnlyB {
    pub b: i64,
}

impl Default for functions_03_argument_spread_edges__OnlyB {
    fn default() -> Self {
        Self { b: 0 }
    }
}

fn functions_03_argument_spread_edges__ignored_args() -> functions_03_argument_spread_edges__Args {
    println!("ignore args");
    return functions_03_argument_spread_edges__Args { a: 9, b: 9, c: 9, extra: 99 };
}

fn functions_03_argument_spread_edges__noisy_args() -> functions_03_argument_spread_edges__Args {
    println!("make args");
    return functions_03_argument_spread_edges__Args { a: 3, b: 2, c: 1, extra: 99 };
}

fn functions_03_argument_spread_edges__pack_i64_i64_i64(a: i64, b: i64, c: i64) -> i64 {
    return (((a * 100) + (b * 10)) + c);
}

fn main() {
    let left = functions_03_argument_spread_edges__AB { a: 1, b: 2 };
    let right = functions_03_argument_spread_edges__BC { b: 7, c: 8 };
    let only_b = functions_03_argument_spread_edges__OnlyB { b: 4 };
    let holder = functions_03_argument_spread_edges__Holder { nested: functions_03_argument_spread_edges__Args { a: 6, b: 5, c: 4, extra: 0 } };
    let bad = functions_03_argument_spread_edges__BadA { a: String::from("bad"), b: 8, c: 9 };
    println!("{}", functions_03_argument_spread_edges__pack_i64_i64_i64(left.a, right.b, right.c));
    println!("{}", functions_03_argument_spread_edges__pack_i64_i64_i64(left.a, left.b, 5));
    println!("{}", functions_03_argument_spread_edges__pack_i64_i64_i64(3, only_b.b, 9));
    println!("{}", functions_03_argument_spread_edges__pack_i64_i64_i64(holder.nested.a, holder.nested.b, holder.nested.c));
    println!("{}", functions_03_argument_spread_edges__pack_i64_i64_i64(7, bad.b, bad.c));
    println!("{}", {
        let __zinc_arg_spread_293_295 = functions_03_argument_spread_edges__noisy_args();
        functions_03_argument_spread_edges__pack_i64_i64_i64(__zinc_arg_spread_293_295.a, __zinc_arg_spread_293_295.b, __zinc_arg_spread_293_295.c)
    });
    println!("{}", functions_03_argument_spread_edges__pack_i64_i64_i64(1, 2, 3));
    println!("{}", {
        let __zinc_arg_spread_337_339 = functions_03_argument_spread_edges__noisy_args();
        functions_03_argument_spread_edges__pack_i64_i64_i64(__zinc_arg_spread_337_339.a, __zinc_arg_spread_337_339.b, __zinc_arg_spread_337_339.c)
    });
}