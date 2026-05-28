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

#[derive(Clone, Default)]
struct __ZincAnonStruct_AnonStruct_a_i64_enabled_bool_extra_i64_name_String_z_i64 {
    a: i64,
    enabled: bool,
    extra: i64,
    name: String,
    z: i64,
}

#[derive(Clone, Default)]
struct __ZincAnonStruct_AnonStruct_a_i64_extra_i64_name_String {
    a: i64,
    extra: i64,
    name: String,
}

#[derive(Clone, Default)]
struct __ZincAnonStruct_AnonStruct_enabled_bool_name_String {
    enabled: bool,
    name: String,
}

struct structs_20_struct_spread_edges__BadName {
    pub name: i64,
    pub enabled: bool,
}

impl Default for structs_20_struct_spread_edges__BadName {
    fn default() -> Self {
        Self { name: 0, enabled: false }
    }
}

struct structs_20_struct_spread_edges__Config {
    pub a: i64,
    pub name: String,
    pub enabled: bool,
    pub ratio: f64,
}

impl Default for structs_20_struct_spread_edges__Config {
    fn default() -> Self {
        Self { a: 0, name: String::new(), enabled: false, ratio: 0.0 }
    }
}

struct structs_20_struct_spread_edges__FloatRatio {
    pub ratio: f64,
}

impl Default for structs_20_struct_spread_edges__FloatRatio {
    fn default() -> Self {
        Self { ratio: 0.0 }
    }
}

struct structs_20_struct_spread_edges__Nested {
    pub config: structs_20_struct_spread_edges__Config,
}

impl Default for structs_20_struct_spread_edges__Nested {
    fn default() -> Self {
        Self { config: Default::default() }
    }
}

fn structs_20_struct_spread_edges__ignored_config() -> structs_20_struct_spread_edges__Config {
    println!("ignore config");
    return structs_20_struct_spread_edges__Config { a: 9, name: String::from("ignored"), enabled: true, ratio: 9.5 };
}

fn structs_20_struct_spread_edges__noisy_config() -> structs_20_struct_spread_edges__Config {
    println!("make config");
    return structs_20_struct_spread_edges__Config { a: 8, name: String::from("made"), enabled: true, ratio: 6.5 };
}

fn main() {
    let base = structs_20_struct_spread_edges__Config { a: 1, name: String::from("base"), enabled: false, ratio: 1.5 };
    let bad = structs_20_struct_spread_edges__BadName { name: 404, enabled: true };
    let float_ratio = structs_20_struct_spread_edges__FloatRatio { ratio: 4.25 };
    let nested = structs_20_struct_spread_edges__Nested { config: base };
    let with_extra = __ZincAnonStruct_AnonStruct_a_i64_extra_i64_name_String { a: 4, name: String::from("anon"), extra: 99 };
    let fixed_bad = structs_20_struct_spread_edges__Config { a: 2, name: String::from("fixed"), enabled: bad.enabled, ratio: 2.5 };
    let from_nested = structs_20_struct_spread_edges__Config { a: 7, name: nested.config.name.clone(), enabled: nested.config.enabled, ratio: nested.config.ratio };
    let spread_ratio = structs_20_struct_spread_edges__Config { a: 3, name: String::from("ratio"), enabled: false, ratio: float_ratio.ratio };
    let named_ignores_extra = structs_20_struct_spread_edges__Config { a: with_extra.a, name: with_extra.name.clone(), enabled: true, ratio: 4.5 };
    let noisy = {
        let __zinc_field_spread_242_244 = structs_20_struct_spread_edges__noisy_config();
        structs_20_struct_spread_edges__Config { a: __zinc_field_spread_242_244.a, name: __zinc_field_spread_242_244.name.clone(), enabled: __zinc_field_spread_242_244.enabled, ratio: __zinc_field_spread_242_244.ratio }
    };
    let ignored = structs_20_struct_spread_edges__Config { a: 5, name: String::from("direct"), enabled: false, ratio: 5.5 };
    let anon_left = __ZincAnonStruct_AnonStruct_a_i64_extra_i64_name_String { a: 10, name: String::from("left"), extra: 1 };
    let anon_right = __ZincAnonStruct_AnonStruct_enabled_bool_name_String { name: String::from("right"), enabled: true };
    let anon_union = __ZincAnonStruct_AnonStruct_a_i64_enabled_bool_extra_i64_name_String_z_i64 { z: 0, a: 11, name: anon_right.name.clone(), extra: anon_left.extra, enabled: anon_right.enabled };
    println!("{}", fixed_bad.name);
    println!("{}", fixed_bad.enabled);
    println!("{}", from_nested.a);
    println!("{}", from_nested.name);
    println!("{}", spread_ratio.ratio);
    println!("{}", named_ignores_extra.name);
    println!("{}", named_ignores_extra.enabled);
    println!("{}", noisy.a);
    println!("{}", noisy.name);
    println!("{}", ignored.a);
    println!("{}", ignored.name);
    println!("{}", anon_union.z);
    println!("{}", anon_union.a);
    println!("{}", anon_union.name);
    println!("{}", anon_union.enabled);
    println!("{}", anon_union.extra);
}