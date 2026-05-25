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
struct __ZincClosureEnv_closures_05_sibling_closures_shared_cell___lambda_closures_05_sibling_closures_shared_cell__make_pair_10_19 {
    count: Arc<Mutex<i64>>,
}

#[derive(Clone)]
struct __ZincClosureEnv_closures_05_sibling_closures_shared_cell___lambda_closures_05_sibling_closures_shared_cell__make_pair_22_30 {
    count: Arc<Mutex<i64>>,
}

#[derive(Clone)]
enum __ZincCallable_Unit_to_Unit {
    Closed,
    V0(__ZincClosureEnv_closures_05_sibling_closures_shared_cell___lambda_closures_05_sibling_closures_shared_cell__make_pair_10_19),
    V1(__ZincClosureEnv_closures_05_sibling_closures_shared_cell___lambda_closures_05_sibling_closures_shared_cell__make_pair_22_30),
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
            Self::V0(env) => { closures_05_sibling_closures_shared_cell____lambda_closures_05_sibling_closures_shared_cell__make_pair_10_19(env.clone()); }
            Self::V1(env) => { closures_05_sibling_closures_shared_cell____lambda_closures_05_sibling_closures_shared_cell__make_pair_22_30(env.clone()); }
        }
    }
}

fn closures_05_sibling_closures_shared_cell____lambda_closures_05_sibling_closures_shared_cell__make_pair_10_19(__env: __ZincClosureEnv_closures_05_sibling_closures_shared_cell___lambda_closures_05_sibling_closures_shared_cell__make_pair_10_19) {
    let __zv_closures_05_sibling_closures_shared_cell____lambda_closures_05_sibling_closures_shared_cell__make_pair_10_19_count_i64 = __env.count.clone();
    let __zinc_captured_write_14_18 = (*__zv_closures_05_sibling_closures_shared_cell____lambda_closures_05_sibling_closures_shared_cell__make_pair_10_19_count_i64.lock().unwrap() + 1);
    *__zv_closures_05_sibling_closures_shared_cell____lambda_closures_05_sibling_closures_shared_cell__make_pair_10_19_count_i64.lock().unwrap() = __zinc_captured_write_14_18;
}

fn closures_05_sibling_closures_shared_cell____lambda_closures_05_sibling_closures_shared_cell__make_pair_22_30(__env: __ZincClosureEnv_closures_05_sibling_closures_shared_cell___lambda_closures_05_sibling_closures_shared_cell__make_pair_22_30) {
    let __zv_closures_05_sibling_closures_shared_cell____lambda_closures_05_sibling_closures_shared_cell__make_pair_22_30_count_i64 = __env.count.clone();
    println!("{}", *__zv_closures_05_sibling_closures_shared_cell____lambda_closures_05_sibling_closures_shared_cell__make_pair_22_30_count_i64.lock().unwrap());
}

fn closures_05_sibling_closures_shared_cell__make_pair() -> (__ZincCallable_Unit_to_Unit, __ZincCallable_Unit_to_Unit) {
    let __zv_closures_05_sibling_closures_shared_cell__make_pair_count_i64 = Arc::new(Mutex::new(0));
    let inc = __ZincCallable_Unit_to_Unit::V0(__ZincClosureEnv_closures_05_sibling_closures_shared_cell___lambda_closures_05_sibling_closures_shared_cell__make_pair_10_19 { count: __zv_closures_05_sibling_closures_shared_cell__make_pair_count_i64.clone() });
    let read = __ZincCallable_Unit_to_Unit::V1(__ZincClosureEnv_closures_05_sibling_closures_shared_cell___lambda_closures_05_sibling_closures_shared_cell__make_pair_22_30 { count: __zv_closures_05_sibling_closures_shared_cell__make_pair_count_i64.clone() });
    return (inc, read);
}

fn main() {
    let (inc, read) = closures_05_sibling_closures_shared_cell__make_pair();
    inc.call();
    read.call();
    inc.call();
    read.call();
}