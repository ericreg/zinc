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
struct __ZincClosureEnv_decorators_01_stacked_and_generic___lambda_decorators_01_stacked_and_generic____lambda_decorators_01_stacked_and_generic__labeler_String_60_89_i64_to_i64_72_88 {
    label: Arc<Mutex<String>>,
    f: Arc<Mutex<__ZincCallable_i64_to_i64>>,
}

#[derive(Clone)]
struct __ZincClosureEnv_decorators_01_stacked_and_generic___lambda_decorators_01_stacked_and_generic__labeler_String_60_89 {
    label: Arc<Mutex<String>>,
}

#[derive(Clone)]
struct __ZincClosureEnv_decorators_01_stacked_and_generic___lambda_decorators_01_stacked_and_generic__logged_i64_to_i64_19_35 {
    f: Arc<Mutex<__ZincCallable_i64_to_i64>>,
}

#[derive(Clone)]
enum __ZincCallable_String_to_String {
    Closed,
    V0,
}

impl Default for __ZincCallable_String_to_String {
    fn default() -> Self {
        Self::Closed
    }
}

impl __ZincCallable_String_to_String {
    fn call(&self, arg_0: String) -> String {
        match self {
            Self::Closed => panic!("callable used after closed receive"),
            Self::V0 => decorators_01_stacked_and_generic__echo_String__zinc_impl(arg_0),
        }
    }
}

#[derive(Clone)]
enum __ZincCallable_i64_to_i64 {
    Closed,
    V0(__ZincClosureEnv_decorators_01_stacked_and_generic___lambda_decorators_01_stacked_and_generic____lambda_decorators_01_stacked_and_generic__labeler_String_60_89_i64_to_i64_72_88),
    V1(__ZincClosureEnv_decorators_01_stacked_and_generic___lambda_decorators_01_stacked_and_generic__logged_i64_to_i64_19_35),
    V2,
    V3,
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
            Self::V0(env) => decorators_01_stacked_and_generic____lambda_decorators_01_stacked_and_generic____lambda_decorators_01_stacked_and_generic__labeler_String_60_89_i64_to_i64_72_88_i64(env.clone(), arg_0),
            Self::V1(env) => decorators_01_stacked_and_generic____lambda_decorators_01_stacked_and_generic__logged_i64_to_i64_19_35_i64(env.clone(), arg_0),
            Self::V2 => decorators_01_stacked_and_generic__echo_i64__zinc_impl(arg_0),
            Self::V3 => decorators_01_stacked_and_generic__inc_i64__zinc_impl(arg_0),
        }
    }
}

#[derive(Clone)]
enum __ZincCallable_i64_to_i64_to_i64_to_i64 {
    Closed,
    V0(__ZincClosureEnv_decorators_01_stacked_and_generic___lambda_decorators_01_stacked_and_generic__labeler_String_60_89),
}

impl Default for __ZincCallable_i64_to_i64_to_i64_to_i64 {
    fn default() -> Self {
        Self::Closed
    }
}

impl __ZincCallable_i64_to_i64_to_i64_to_i64 {
    fn call(&self, arg_0: __ZincCallable_i64_to_i64) -> __ZincCallable_i64_to_i64 {
        match self {
            Self::Closed => panic!("callable used after closed receive"),
            Self::V0(env) => decorators_01_stacked_and_generic____lambda_decorators_01_stacked_and_generic__labeler_String_60_89_i64_to_i64(env.clone(), arg_0),
        }
    }
}

fn decorators_01_stacked_and_generic____lambda_decorators_01_stacked_and_generic____lambda_decorators_01_stacked_and_generic__labeler_String_60_89_i64_to_i64_72_88_i64(__env: __ZincClosureEnv_decorators_01_stacked_and_generic___lambda_decorators_01_stacked_and_generic____lambda_decorators_01_stacked_and_generic__labeler_String_60_89_i64_to_i64_72_88, x: i64) -> i64 {
    let __zv_decorators_01_stacked_and_generic____lambda_decorators_01_stacked_and_generic____lambda_decorators_01_stacked_and_generic__labeler_String_60_89_i64_to_i64_72_88_i64_label_String = __env.label.clone();
    let __zv_decorators_01_stacked_and_generic____lambda_decorators_01_stacked_and_generic____lambda_decorators_01_stacked_and_generic__labeler_String_60_89_i64_to_i64_72_88_i64_f_i64_i64 = __env.f.clone();
    println!("{}", __zv_decorators_01_stacked_and_generic____lambda_decorators_01_stacked_and_generic____lambda_decorators_01_stacked_and_generic__labeler_String_60_89_i64_to_i64_72_88_i64_label_String.lock().unwrap().clone());
    return __zv_decorators_01_stacked_and_generic____lambda_decorators_01_stacked_and_generic____lambda_decorators_01_stacked_and_generic__labeler_String_60_89_i64_to_i64_72_88_i64_f_i64_i64.lock().unwrap().clone().call(x);
}

fn decorators_01_stacked_and_generic____lambda_decorators_01_stacked_and_generic__labeler_String_60_89_i64_to_i64(__env: __ZincClosureEnv_decorators_01_stacked_and_generic___lambda_decorators_01_stacked_and_generic__labeler_String_60_89, f: __ZincCallable_i64_to_i64) -> __ZincCallable_i64_to_i64 {
    let __zv_decorators_01_stacked_and_generic____lambda_decorators_01_stacked_and_generic__labeler_String_60_89_i64_to_i64_label_String = __env.label.clone();
    let __zv_decorators_01_stacked_and_generic____lambda_decorators_01_stacked_and_generic__labeler_String_60_89_i64_to_i64_f_i64_i64 = Arc::new(Mutex::new(f));
    return __ZincCallable_i64_to_i64::V0(__ZincClosureEnv_decorators_01_stacked_and_generic___lambda_decorators_01_stacked_and_generic____lambda_decorators_01_stacked_and_generic__labeler_String_60_89_i64_to_i64_72_88 { label: __zv_decorators_01_stacked_and_generic____lambda_decorators_01_stacked_and_generic__labeler_String_60_89_i64_to_i64_label_String.clone(), f: __zv_decorators_01_stacked_and_generic____lambda_decorators_01_stacked_and_generic__labeler_String_60_89_i64_to_i64_f_i64_i64.clone() });
}

fn decorators_01_stacked_and_generic__labeler_String(label: String) -> __ZincCallable_i64_to_i64_to_i64_to_i64 {
    let __zv_decorators_01_stacked_and_generic__labeler_String_label_String = Arc::new(Mutex::new(label));
    return __ZincCallable_i64_to_i64_to_i64_to_i64::V0(__ZincClosureEnv_decorators_01_stacked_and_generic___lambda_decorators_01_stacked_and_generic__labeler_String_60_89 { label: __zv_decorators_01_stacked_and_generic__labeler_String_label_String.clone() });
}

fn decorators_01_stacked_and_generic__logged_i64_to_i64(f: __ZincCallable_i64_to_i64) -> __ZincCallable_i64_to_i64 {
    let __zv_decorators_01_stacked_and_generic__logged_i64_to_i64_f_i64_i64 = Arc::new(Mutex::new(f));
    return __ZincCallable_i64_to_i64::V1(__ZincClosureEnv_decorators_01_stacked_and_generic___lambda_decorators_01_stacked_and_generic__logged_i64_to_i64_19_35 { f: __zv_decorators_01_stacked_and_generic__logged_i64_to_i64_f_i64_i64.clone() });
}

fn decorators_01_stacked_and_generic__inc_i64__zinc_impl(x: i64) -> i64 {
    return (x + 1);
}

fn decorators_01_stacked_and_generic__inc_i64(x: i64) -> i64 {
    let __zinc_decorated_0 = __ZincCallable_i64_to_i64::V3;
    let __zinc_decorated_1 = decorators_01_stacked_and_generic__logged_i64_to_i64(__zinc_decorated_0.clone());
    let __zinc_decorator_factory_2 = decorators_01_stacked_and_generic__labeler_String(String::from("outer"));
    let __zinc_decorated_2 = __zinc_decorator_factory_2.call(__zinc_decorated_1.clone());
    return __zinc_decorated_2.call(x);
}

fn decorators_01_stacked_and_generic____lambda_decorators_01_stacked_and_generic__logged_i64_to_i64_19_35_i64(__env: __ZincClosureEnv_decorators_01_stacked_and_generic___lambda_decorators_01_stacked_and_generic__logged_i64_to_i64_19_35, x: i64) -> i64 {
    let __zv_decorators_01_stacked_and_generic____lambda_decorators_01_stacked_and_generic__logged_i64_to_i64_19_35_i64_f_i64_i64 = __env.f.clone();
    println!("logged");
    return __zv_decorators_01_stacked_and_generic____lambda_decorators_01_stacked_and_generic__logged_i64_to_i64_19_35_i64_f_i64_i64.lock().unwrap().clone().call(x);
}

fn decorators_01_stacked_and_generic__identity_dec_String_to_String(f: __ZincCallable_String_to_String) -> __ZincCallable_String_to_String {
    return f;
}

fn decorators_01_stacked_and_generic__echo_String__zinc_impl(x: String) -> String {
    return x;
}

fn decorators_01_stacked_and_generic__echo_String(x: String) -> String {
    let __zinc_decorated_0 = __ZincCallable_String_to_String::V0;
    let __zinc_decorated_1 = decorators_01_stacked_and_generic__identity_dec_String_to_String(__zinc_decorated_0.clone());
    return __zinc_decorated_1.call(x);
}

fn decorators_01_stacked_and_generic__identity_dec_i64_to_i64(f: __ZincCallable_i64_to_i64) -> __ZincCallable_i64_to_i64 {
    return f;
}

fn decorators_01_stacked_and_generic__echo_i64__zinc_impl(x: i64) -> i64 {
    return x;
}

fn decorators_01_stacked_and_generic__echo_i64(x: i64) -> i64 {
    let __zinc_decorated_0 = __ZincCallable_i64_to_i64::V2;
    let __zinc_decorated_1 = decorators_01_stacked_and_generic__identity_dec_i64_to_i64(__zinc_decorated_0.clone());
    return __zinc_decorated_1.call(x);
}

fn main() {
    println!("{}", decorators_01_stacked_and_generic__inc_i64(3));
    println!("{}", decorators_01_stacked_and_generic__echo_i64(7));
    println!("{}", decorators_01_stacked_and_generic__echo_String(String::from("hi")));
}