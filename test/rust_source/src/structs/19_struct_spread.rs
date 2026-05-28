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
struct __ZincAnonStruct_AnonStruct_a_i64_enabled_bool_extra_i64_name_String {
    a: i64,
    enabled: bool,
    extra: i64,
    name: String,
}

#[derive(Clone, Default)]
struct __ZincAnonStruct_AnonStruct_a_i64_enabled_bool_name_String {
    a: i64,
    enabled: bool,
    name: String,
}

#[derive(Clone, Default)]
struct __ZincAnonStruct_AnonStruct_x_i64_y_i64 {
    x: i64,
    y: i64,
}

struct structs_19_struct_spread__Config {
    pub a: i64,
    pub name: String,
    pub enabled: bool,
    pub ratio: f64,
}

impl Default for structs_19_struct_spread__Config {
    fn default() -> Self {
        Self { a: 0, name: String::new(), enabled: false, ratio: 0.0 }
    }
}

struct structs_19_struct_spread__PartialConfig {
    pub name: String,
    pub enabled: bool,
}

impl Default for structs_19_struct_spread__PartialConfig {
    fn default() -> Self {
        Self { name: String::new(), enabled: false }
    }
}

fn structs_19_struct_spread__make_config() -> structs_19_struct_spread__Config {
    return structs_19_struct_spread__Config { a: 7, name: String::from("made"), enabled: true, ratio: 4.5 };
}

fn main() {
    let base = structs_19_struct_spread__Config { a: 1, name: String::from("base"), enabled: false, ratio: 1.5 };
    let partial = structs_19_struct_spread__PartialConfig { name: String::from("partial"), enabled: true };
    let right_override = structs_19_struct_spread__Config { a: 2, name: String::from("right"), enabled: base.enabled, ratio: base.ratio };
    let left_override = structs_19_struct_spread__Config { a: base.a, name: base.name.clone(), enabled: base.enabled, ratio: base.ratio };
    let filled = structs_19_struct_spread__Config { a: 4, name: partial.name.clone(), enabled: partial.enabled, ratio: 2.5 };
    let layered = structs_19_struct_spread__Config { a: filled.a, name: filled.name.clone(), enabled: false, ratio: filled.ratio };
    let made = {
        let __zinc_field_spread_154_156 = structs_19_struct_spread__make_config();
        structs_19_struct_spread__Config { a: 8, name: __zinc_field_spread_154_156.name.clone(), enabled: __zinc_field_spread_154_156.enabled, ratio: __zinc_field_spread_154_156.ratio }
    };
    let duplicate = structs_19_struct_spread__Config { a: 6, name: String::from("dupe"), enabled: true, ratio: 3.5 };
    let anon_base = __ZincAnonStruct_AnonStruct_a_i64_enabled_bool_name_String { a: 5, name: String::from("anon"), enabled: true };
    let anon = __ZincAnonStruct_AnonStruct_a_i64_enabled_bool_extra_i64_name_String { a: anon_base.a, name: String::from("later"), enabled: anon_base.enabled, extra: 9 };
    let anon_duplicate = __ZincAnonStruct_AnonStruct_x_i64_y_i64 { x: 3, y: 2 };
    println!("{}", right_override.a);
    println!("{}", right_override.name);
    println!("{}", left_override.a);
    println!("{}", left_override.name);
    println!("{}", filled.name);
    println!("{}", filled.enabled);
    println!("{}", layered.a);
    println!("{}", layered.name);
    println!("{}", layered.enabled);
    println!("{}", made.a);
    println!("{}", made.name);
    println!("{}", duplicate.name);
    println!("{}", duplicate.enabled);
    println!("{}", anon.a);
    println!("{}", anon.name);
    println!("{}", anon.extra);
    println!("{}", anon_duplicate.x);
}