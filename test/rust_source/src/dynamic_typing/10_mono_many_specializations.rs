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

fn dynamic_typing_10_mono_many_specializations__add_f64_f64(a: f64, b: f64) -> f64 {
    return (a + b);
}

fn dynamic_typing_10_mono_many_specializations__add_f64_i64(a: f64, b: i64) -> f64 {
    return (a + (b as f64));
}

fn dynamic_typing_10_mono_many_specializations__add_i64_f64(a: i64, b: f64) -> f64 {
    return ((a as f64) + b);
}

fn dynamic_typing_10_mono_many_specializations__add_i64_i64(a: i64, b: i64) -> i64 {
    return (a + b);
}

fn dynamic_typing_10_mono_many_specializations__identity_String(x: String) -> String {
    return x;
}

fn dynamic_typing_10_mono_many_specializations__identity_bool(x: bool) -> bool {
    return x;
}

fn dynamic_typing_10_mono_many_specializations__identity_f64(x: f64) -> f64 {
    return x;
}

fn dynamic_typing_10_mono_many_specializations__identity_i64(x: i64) -> i64 {
    return x;
}

fn dynamic_typing_10_mono_many_specializations__process_f64_f64_f64(x: f64, y: f64, z: f64) -> f64 {
    return ((x + y) + z);
}

fn dynamic_typing_10_mono_many_specializations__process_i64_f64_i64(x: i64, y: f64, z: i64) -> f64 {
    return (((x as f64) + y) + (z as f64));
}

fn dynamic_typing_10_mono_many_specializations__process_i64_i64_i64(x: i64, y: i64, z: i64) -> i64 {
    return ((x + y) + z);
}

fn main() {
    let a = dynamic_typing_10_mono_many_specializations__identity_i64(1);
    println!("identity(int): {}", a);
    let b = dynamic_typing_10_mono_many_specializations__identity_f64(3.14);
    println!("identity(float): {}", b);
    let c = dynamic_typing_10_mono_many_specializations__identity_bool(true);
    println!("identity(bool): {}", c);
    let d = dynamic_typing_10_mono_many_specializations__identity_String(String::from("hello"));
    println!("identity(string): {}", d);
    let e = dynamic_typing_10_mono_many_specializations__add_i64_i64(1, 2);
    println!("add(int, int): {}", e);
    let f = dynamic_typing_10_mono_many_specializations__add_f64_f64(1.0, 2.0);
    println!("add(float, float): {}", f);
    let g = dynamic_typing_10_mono_many_specializations__add_i64_f64(1, 2.0);
    println!("add(int, float): {}", g);
    let h = dynamic_typing_10_mono_many_specializations__add_f64_i64(1.0, 2);
    println!("add(float, int): {}", h);
    let i = dynamic_typing_10_mono_many_specializations__process_i64_i64_i64(1, 2, 3);
    println!("process(int, int, int): {}", i);
    let j = dynamic_typing_10_mono_many_specializations__process_f64_f64_f64(1.0, 2.0, 3.0);
    println!("process(float, float, float): {}", j);
    let k = dynamic_typing_10_mono_many_specializations__process_i64_f64_i64(1, 2.0, 3);
    println!("process(int, float, int): {}", k);
    let l = dynamic_typing_10_mono_many_specializations__add_i64_f64(10, 0.5);
    println!("add(10, 0.5): {}", l);
}