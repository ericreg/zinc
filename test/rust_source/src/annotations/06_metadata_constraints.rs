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
struct __ZincAnonStruct_AnonStruct_a_bool_b_String {
    a: bool,
    b: String,
}

#[derive(Clone)]
enum annotations_06_metadata_constraints__Color {
    Red,
    Blue,
}

struct annotations_06_metadata_constraints__Audit {
    pub created_at: i64,
}

impl Default for annotations_06_metadata_constraints__Audit {
    fn default() -> Self {
        Self { created_at: 0 }
    }
}

struct annotations_06_metadata_constraints__Circle {
    pub name: String,
    pub radius: f64,
}

impl Default for annotations_06_metadata_constraints__Circle {
    fn default() -> Self {
        Self { name: String::new(), radius: 0.0 }
    }
}

impl annotations_06_metadata_constraints__Circle {
    fn area(&self) -> f64 {
        return (self.radius * self.radius);
    }
}

struct annotations_06_metadata_constraints__Named {
    pub name: String,
}

impl Default for annotations_06_metadata_constraints__Named {
    fn default() -> Self {
        Self { name: String::new() }
    }
}

// infer-backed struct family annotations_06_metadata_constraints__Pair uses synthesized concrete shapes

struct annotations_06_metadata_constraints__Rectangle {
    pub name: String,
    pub width: i64,
}

impl Default for annotations_06_metadata_constraints__Rectangle {
    fn default() -> Self {
        Self { name: String::new(), width: 0 }
    }
}

impl annotations_06_metadata_constraints__Rectangle {
    fn area(&self) -> i64 {
        return self.width;
    }
}

struct annotations_06_metadata_constraints__Shape2D {
    pub name: String,
}

impl Default for annotations_06_metadata_constraints__Shape2D {
    fn default() -> Self {
        Self { name: String::new() }
    }
}

impl annotations_06_metadata_constraints__Shape2D {
    fn area() -> i64 {
        return 0;
    }
}

struct annotations_06_metadata_constraints__TaggedCircle {
    pub created_at: i64,
    pub name: String,
    pub radius: f64,
    pub tag: String,
}

impl Default for annotations_06_metadata_constraints__TaggedCircle {
    fn default() -> Self {
        Self { created_at: 0, name: String::new(), radius: 0.0, tag: String::new() }
    }
}

impl annotations_06_metadata_constraints__TaggedCircle {
    fn area(&self) -> f64 {
        return (self.radius * self.radius);
    }
}

fn annotations_06_metadata_constraints__print_shape_Struct_annotations_06_metadata_constraints_Rectangle(shape: annotations_06_metadata_constraints__Rectangle) {
    println!("{}", String::from("print_shape"));
    println!("{}", shape.name);
    println!("{}", shape.area());
}

fn main() {
    println!("{}", 58);
    let pair = __ZincAnonStruct_AnonStruct_a_bool_b_String { a: true, b: String::from("ok") };
    let item = annotations_06_metadata_constraints__TaggedCircle { created_at: 7, name: String::from("circle"), radius: 3.0, tag: String::from("featured") };
    println!("{}", String::from("enum"));
    println!("{}", 1);
    println!("{}", String::from("Color"));
    println!("{}", String::from("builtin"));
    println!("{}", String::from("Pair"));
    println!("{}", String::from("bool"));
    println!("{}", String::from("String"));
    println!("{}", String::from("b"));
    println!("{}", String::from("Red"));
    println!("{}", String::from("created_at"));
    println!("{}", false);
    println!("{}", String::from("annotations/06_metadata_constraints/Audit"));
    println!("{}", String::from("tag"));
    println!("{}", true);
    println!("{}", String::from("Circle"));
    println!("{}", String::from("Shape2D"));
    println!("{}", String::from("Named"));
    println!("{}", String::from("TaggedCircle"));
    println!("{}", String::from("TaggedCircle"));
    println!("{}", false);
    println!("{}", true);
    println!("{}", false);
    println!("{}", true);
    annotations_06_metadata_constraints__print_shape_Struct_annotations_06_metadata_constraints_Rectangle(annotations_06_metadata_constraints__Rectangle { name: String::from("box"), width: 9 });
}