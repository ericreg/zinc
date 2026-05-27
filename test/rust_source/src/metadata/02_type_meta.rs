use std::collections::{HashMap, HashSet};

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

#[derive(Clone, Debug, Default, PartialEq)]
struct __ZincTypeMeta {
    pub kind: String,
    pub name: String,
    pub fqn: String,
    pub family_name: String,
    pub family_fqn: String,
    pub args: Vec<__ZincTypeMeta>,
    pub is_named: bool,
    pub is_bounded: bool,
    pub infer_slots: Vec<String>,
}

#[derive(Clone, Debug, Default, PartialEq)]
struct __ZincStructMeta {
    pub kind: String,
    pub name: String,
    pub fqn: String,
    pub module_fqn: String,
    pub file: String,
    pub line_num: u32,
    pub is_public: bool,
    pub type_info: __ZincTypeMeta,
}

#[derive(Clone, Debug, Default, PartialEq)]
struct __ZincEnumMeta {
    pub kind: String,
    pub name: String,
    pub fqn: String,
    pub module_fqn: String,
    pub file: String,
    pub line_num: u32,
    pub is_public: bool,
    pub type_info: __ZincTypeMeta,
}

#[derive(Clone, Debug, Default, PartialEq)]
struct __ZincVariantMeta {
    pub kind: String,
    pub name: String,
    pub fqn: String,
    pub module_fqn: String,
    pub file: String,
    pub line_num: u32,
    pub is_public: bool,
    pub index: u32,
}

#[derive(Clone, Debug, Default, PartialEq)]
struct __ZincFieldMeta {
    pub kind: String,
    pub name: String,
    pub fqn: String,
    pub module_fqn: String,
    pub file: String,
    pub line_num: u32,
    pub is_public: bool,
    pub value_type: __ZincTypeMeta,
    pub index: u32,
    pub is_const: bool,
    pub has_default: bool,
    pub is_declared: bool,
    pub source_component_fqn: String,
}

#[derive(Clone, Debug, Default, PartialEq)]
struct __ZincFunctionParameterMeta {
    pub kind: String,
    pub name: String,
    pub fqn: String,
    pub module_fqn: String,
    pub file: String,
    pub line_num: u32,
    pub is_public: bool,
    pub index: u32,
    pub value_type: __ZincTypeMeta,
    pub declared_type: __ZincTypeMeta,
    pub has_declared_type: bool,
}

#[derive(Clone, Debug, Default, PartialEq)]
struct __ZincMethodParameterMeta {
    pub kind: String,
    pub name: String,
    pub fqn: String,
    pub module_fqn: String,
    pub file: String,
    pub line_num: u32,
    pub is_public: bool,
    pub index: u32,
    pub value_type: __ZincTypeMeta,
    pub declared_type: __ZincTypeMeta,
    pub has_declared_type: bool,
}

#[derive(Clone, Debug, Default, PartialEq)]
struct __ZincFunctionMeta {
    pub kind: String,
    pub name: String,
    pub fqn: String,
    pub module_fqn: String,
    pub file: String,
    pub line_num: u32,
    pub is_public: bool,
    pub params: Vec<__ZincFunctionParameterMeta>,
    pub return_type: __ZincTypeMeta,
    pub is_async: bool,
}

#[derive(Clone, Debug, Default, PartialEq)]
struct __ZincBuiltinMeta {
    pub kind: String,
    pub name: String,
    pub fqn: String,
    pub module_fqn: String,
    pub file: String,
    pub line_num: u32,
    pub is_public: bool,
    pub params: Vec<__ZincFunctionParameterMeta>,
    pub return_type: __ZincTypeMeta,
    pub is_async: bool,
}

#[derive(Clone, Debug, Default, PartialEq)]
struct __ZincMethodMeta {
    pub kind: String,
    pub name: String,
    pub fqn: String,
    pub module_fqn: String,
    pub file: String,
    pub line_num: u32,
    pub is_public: bool,
    pub params: Vec<__ZincMethodParameterMeta>,
    pub return_type: __ZincTypeMeta,
    pub is_async: bool,
    pub is_static: bool,
    pub is_declared: bool,
}

#[derive(Clone, Debug, Default, PartialEq)]
struct __ZincVariableMeta {
    pub kind: String,
    pub name: String,
    pub fqn: String,
    pub module_fqn: String,
    pub file: String,
    pub line_num: u32,
    pub is_public: bool,
    pub value_type: __ZincTypeMeta,
    pub has_declared_type: bool,
    pub is_mutated: bool,
    pub is_shadow: bool,
}

#[derive(Clone, Debug, Default, PartialEq)]
struct __ZincConstMeta {
    pub kind: String,
    pub name: String,
    pub fqn: String,
    pub module_fqn: String,
    pub file: String,
    pub line_num: u32,
    pub is_public: bool,
    pub value_type: __ZincTypeMeta,
    pub value_text: String,
}

#[derive(Clone, Debug, PartialEq)]
enum __ZincComponentOrder {
    DepthFirst,
    BreadthFirst,
    Topological,
}

#[derive(Clone, Default)]
struct __ZincAnonStruct_AnonStruct_x_i64_y_String {
    x: i64,
    y: String,
}

struct metadata_02_type_meta__Base {
    pub version: i64,
    pub name: String,
}

impl Default for metadata_02_type_meta__Base {
    fn default() -> Self {
        Self { version: 1, name: String::new() }
    }
}

struct metadata_02_type_meta__Detail {
    pub level: i64,
}

impl Default for metadata_02_type_meta__Detail {
    fn default() -> Self {
        Self { level: 0 }
    }
}

impl metadata_02_type_meta__Detail {
    fn scale(&self, multiplier: i64) -> i64 {
        return (self.level * multiplier);
    }
}

struct metadata_02_type_meta__Node {
    pub version: i64,
    pub name: String,
    pub level: i64,
    pub enabled: bool,
}

impl Default for metadata_02_type_meta__Node {
    fn default() -> Self {
        Self { version: 1, name: String::new(), level: 0, enabled: false }
    }
}

impl metadata_02_type_meta__Node {
    fn scale(&self, multiplier: i64) -> i64 {
        return (self.level * multiplier);
    }
}

// infer-backed struct family metadata_02_type_meta__Pair uses synthesized concrete shapes

#[tokio::main]
async fn main() {
    let pair = __ZincAnonStruct_AnonStruct_x_i64_y_String { x: 7, y: String::from("seven") };
    let node = metadata_02_type_meta__Node { version: 1, name: String::from("root"), level: 2, enabled: true };
    let arr = vec![1, 2, 3];
    let tup = (1, String::from("two"), true);
    let scores = HashMap::from([(String::from("a"), 1), (String::from("b"), 2)]);
    let values = HashSet::from([1, 2, 3]);
    let ch = __ZincChannel::<i64>::unbounded();
    ch.send(1).await;
    let got = ch.recv().await;
    let buffered = __ZincChannel::<String>::bounded(2);
    buffered.send(String::from("ready")).await;
    let buffered_value = buffered.recv().await;
    println!("{:?}", __ZincTypeMeta { kind: String::from("primitive"), name: String::from("i64"), fqn: String::from("i64"), family_name: String::from("i64"), family_fqn: String::from("i64"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() });
    println!("{:?}", __ZincTypeMeta { kind: String::from("primitive"), name: String::from("i64"), fqn: String::from("i64"), family_name: String::from("i64"), family_fqn: String::from("i64"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() });
    println!("{:?}", __ZincTypeMeta { kind: String::from("primitive"), name: String::from("bool"), fqn: String::from("bool"), family_name: String::from("bool"), family_fqn: String::from("bool"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() });
    println!("{:?}", __ZincTypeMeta { kind: String::from("array"), name: String::from("[i64]"), fqn: String::from("[i64]"), family_name: String::from("array"), family_fqn: String::from("array"), args: vec![__ZincTypeMeta { kind: String::from("primitive"), name: String::from("i64"), fqn: String::from("i64"), family_name: String::from("i64"), family_fqn: String::from("i64"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }], is_named: false, is_bounded: false, infer_slots: Vec::<String>::new() });
    println!("{:?}", __ZincTypeMeta { kind: String::from("dict"), name: String::from("dict<String, i64>"), fqn: String::from("dict<String, i64>"), family_name: String::from("dict"), family_fqn: String::from("dict"), args: vec![__ZincTypeMeta { kind: String::from("primitive"), name: String::from("String"), fqn: String::from("String"), family_name: String::from("String"), family_fqn: String::from("String"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, __ZincTypeMeta { kind: String::from("primitive"), name: String::from("i64"), fqn: String::from("i64"), family_name: String::from("i64"), family_fqn: String::from("i64"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }], is_named: false, is_bounded: false, infer_slots: Vec::<String>::new() });
    println!("{:?}", __ZincTypeMeta { kind: String::from("set"), name: String::from("set<i64>"), fqn: String::from("set<i64>"), family_name: String::from("set"), family_fqn: String::from("set"), args: vec![__ZincTypeMeta { kind: String::from("primitive"), name: String::from("i64"), fqn: String::from("i64"), family_name: String::from("i64"), family_fqn: String::from("i64"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }], is_named: false, is_bounded: false, infer_slots: Vec::<String>::new() });
    println!("{:?}", __ZincTypeMeta { kind: String::from("tuple"), name: String::from("(i64, String, bool)"), fqn: String::from("(i64, String, bool)"), family_name: String::from("tuple"), family_fqn: String::from("tuple"), args: vec![__ZincTypeMeta { kind: String::from("primitive"), name: String::from("i64"), fqn: String::from("i64"), family_name: String::from("i64"), family_fqn: String::from("i64"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, __ZincTypeMeta { kind: String::from("primitive"), name: String::from("String"), fqn: String::from("String"), family_name: String::from("String"), family_fqn: String::from("String"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, __ZincTypeMeta { kind: String::from("primitive"), name: String::from("bool"), fqn: String::from("bool"), family_name: String::from("bool"), family_fqn: String::from("bool"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }], is_named: false, is_bounded: false, infer_slots: Vec::<String>::new() });
    println!("{}", String::from("callable"));
    println!("{:?}", __ZincTypeMeta { kind: String::from("channel"), name: String::from("channel<i64>"), fqn: String::from("channel<i64>"), family_name: String::from("channel"), family_fqn: String::from("channel"), args: vec![__ZincTypeMeta { kind: String::from("primitive"), name: String::from("i64"), fqn: String::from("i64"), family_name: String::from("i64"), family_fqn: String::from("i64"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }], is_named: false, is_bounded: false, infer_slots: Vec::<String>::new() });
    println!("{}", String::from("i64"));
    println!("{}", false);
    println!("{}", String::from("ChannelMeta"));
    println!("{:?}", __ZincTypeMeta { kind: String::from("channel"), name: String::from("channel<String>"), fqn: String::from("channel<String>"), family_name: String::from("channel"), family_fqn: String::from("channel"), args: vec![__ZincTypeMeta { kind: String::from("primitive"), name: String::from("String"), fqn: String::from("String"), family_name: String::from("String"), family_fqn: String::from("String"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }], is_named: false, is_bounded: true, infer_slots: Vec::<String>::new() });
    println!("{}", String::from("String"));
    println!("{}", true);
    println!("{}", String::from("ChannelMeta"));
    println!("{}", String::from("i64"));
    println!("{}", String::from("String"));
    println!("{}", String::from("ComponentOrder"));
    println!("{:?}", __ZincTypeMeta { kind: String::from("struct"), name: String::from("Pair<i64, String>"), fqn: String::from("metadata/02_type_meta/Pair<i64, String>"), family_name: String::from("Pair"), family_fqn: String::from("metadata/02_type_meta/Pair"), args: vec![__ZincTypeMeta { kind: String::from("primitive"), name: String::from("i64"), fqn: String::from("i64"), family_name: String::from("i64"), family_fqn: String::from("i64"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, __ZincTypeMeta { kind: String::from("primitive"), name: String::from("String"), fqn: String::from("String"), family_name: String::from("String"), family_fqn: String::from("String"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }], is_named: true, is_bounded: false, infer_slots: vec![String::from("x"), String::from("y")] });
    println!("{:?}", vec![__ZincTypeMeta { kind: String::from("primitive"), name: String::from("i64"), fqn: String::from("i64"), family_name: String::from("i64"), family_fqn: String::from("i64"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, __ZincTypeMeta { kind: String::from("primitive"), name: String::from("String"), fqn: String::from("String"), family_name: String::from("String"), family_fqn: String::from("String"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }]);
    println!("{:?}", vec![String::from("x"), String::from("y")]);
    println!("{:?}", __ZincTypeMeta { kind: String::from("struct"), name: String::from("Node"), fqn: String::from("metadata/02_type_meta/Node"), family_name: String::from("Node"), family_fqn: String::from("metadata/02_type_meta/Node"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() });
    println!("{:?}", __ZincTypeMeta { kind: String::from("struct"), name: String::from("Node"), fqn: String::from("metadata/02_type_meta/Node"), family_name: String::from("Node"), family_fqn: String::from("metadata/02_type_meta/Node"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() });
    println!("{:?}", vec![__ZincFieldMeta { kind: String::from("field"), name: String::from("version"), fqn: String::from("metadata/02_type_meta/Node/version"), module_fqn: String::from("metadata/02_type_meta"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/02_type_meta.zn"), line_num: 11, is_public: true, value_type: __ZincTypeMeta { kind: String::from("primitive"), name: String::from("i64"), fqn: String::from("i64"), family_name: String::from("i64"), family_fqn: String::from("i64"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, index: 0, is_const: true, has_default: true, is_declared: false, source_component_fqn: String::from("metadata/02_type_meta/Base") }, __ZincFieldMeta { kind: String::from("field"), name: String::from("name"), fqn: String::from("metadata/02_type_meta/Node/name"), module_fqn: String::from("metadata/02_type_meta"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/02_type_meta.zn"), line_num: 12, is_public: true, value_type: __ZincTypeMeta { kind: String::from("primitive"), name: String::from("String"), fqn: String::from("String"), family_name: String::from("String"), family_fqn: String::from("String"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, index: 1, is_const: false, has_default: false, is_declared: false, source_component_fqn: String::from("metadata/02_type_meta/Base") }, __ZincFieldMeta { kind: String::from("field"), name: String::from("level"), fqn: String::from("metadata/02_type_meta/Node/level"), module_fqn: String::from("metadata/02_type_meta"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/02_type_meta.zn"), line_num: 16, is_public: true, value_type: __ZincTypeMeta { kind: String::from("primitive"), name: String::from("i64"), fqn: String::from("i64"), family_name: String::from("i64"), family_fqn: String::from("i64"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, index: 2, is_const: false, has_default: false, is_declared: false, source_component_fqn: String::from("metadata/02_type_meta/Detail") }, __ZincFieldMeta { kind: String::from("field"), name: String::from("enabled"), fqn: String::from("metadata/02_type_meta/Node/enabled"), module_fqn: String::from("metadata/02_type_meta"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/02_type_meta.zn"), line_num: 24, is_public: true, value_type: __ZincTypeMeta { kind: String::from("primitive"), name: String::from("bool"), fqn: String::from("bool"), family_name: String::from("bool"), family_fqn: String::from("bool"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, index: 3, is_const: false, has_default: false, is_declared: true, source_component_fqn: String::from("") }]);
    println!("{:?}", __ZincFieldMeta { kind: String::from("field"), name: String::from("version"), fqn: String::from("metadata/02_type_meta/Node/version"), module_fqn: String::from("metadata/02_type_meta"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/02_type_meta.zn"), line_num: 11, is_public: true, value_type: __ZincTypeMeta { kind: String::from("primitive"), name: String::from("i64"), fqn: String::from("i64"), family_name: String::from("i64"), family_fqn: String::from("i64"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, index: 0, is_const: true, has_default: true, is_declared: false, source_component_fqn: String::from("metadata/02_type_meta/Base") });
    println!("{}", String::from("Node"));
    println!("{:?}", vec![__ZincMethodMeta { kind: String::from("method"), name: String::from("scale"), fqn: String::from("metadata/02_type_meta/Node/scale"), module_fqn: String::from("metadata/02_type_meta"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/02_type_meta.zn"), line_num: 18, is_public: true, params: vec![__ZincMethodParameterMeta { kind: String::from("parameter"), name: String::from("multiplier"), fqn: String::from("metadata/02_type_meta/Node/scale/multiplier"), module_fqn: String::from("metadata/02_type_meta"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/02_type_meta.zn"), line_num: 18, is_public: false, index: 0, value_type: __ZincTypeMeta { kind: String::from("primitive"), name: String::from("i64"), fqn: String::from("i64"), family_name: String::from("i64"), family_fqn: String::from("i64"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, declared_type: __ZincTypeMeta { kind: String::from("primitive"), name: String::from("i64"), fqn: String::from("i64"), family_name: String::from("i64"), family_fqn: String::from("i64"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, has_declared_type: true }], return_type: __ZincTypeMeta { kind: String::from("primitive"), name: String::from("i64"), fqn: String::from("i64"), family_name: String::from("i64"), family_fqn: String::from("i64"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, is_async: false, is_static: false, is_declared: false }]);
    println!("{:?}", __ZincMethodMeta { kind: String::from("method"), name: String::from("scale"), fqn: String::from("metadata/02_type_meta/Node/scale"), module_fqn: String::from("metadata/02_type_meta"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/02_type_meta.zn"), line_num: 18, is_public: true, params: vec![__ZincMethodParameterMeta { kind: String::from("parameter"), name: String::from("multiplier"), fqn: String::from("metadata/02_type_meta/Node/scale/multiplier"), module_fqn: String::from("metadata/02_type_meta"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/02_type_meta.zn"), line_num: 18, is_public: false, index: 0, value_type: __ZincTypeMeta { kind: String::from("primitive"), name: String::from("i64"), fqn: String::from("i64"), family_name: String::from("i64"), family_fqn: String::from("i64"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, declared_type: __ZincTypeMeta { kind: String::from("primitive"), name: String::from("i64"), fqn: String::from("i64"), family_name: String::from("i64"), family_fqn: String::from("i64"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, has_declared_type: true }], return_type: __ZincTypeMeta { kind: String::from("primitive"), name: String::from("i64"), fqn: String::from("i64"), family_name: String::from("i64"), family_fqn: String::from("i64"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, is_async: false, is_static: false, is_declared: false });
    println!("{}", String::from("Node"));
    println!("{:?}", vec![__ZincTypeMeta { kind: String::from("struct"), name: String::from("Base"), fqn: String::from("metadata/02_type_meta/Base"), family_name: String::from("Base"), family_fqn: String::from("metadata/02_type_meta/Base"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, __ZincTypeMeta { kind: String::from("struct"), name: String::from("Detail"), fqn: String::from("metadata/02_type_meta/Detail"), family_name: String::from("Detail"), family_fqn: String::from("metadata/02_type_meta/Detail"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }]);
    println!("{:?}", vec![__ZincTypeMeta { kind: String::from("struct"), name: String::from("Base"), fqn: String::from("metadata/02_type_meta/Base"), family_name: String::from("Base"), family_fqn: String::from("metadata/02_type_meta/Base"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, __ZincTypeMeta { kind: String::from("struct"), name: String::from("Detail"), fqn: String::from("metadata/02_type_meta/Detail"), family_name: String::from("Detail"), family_fqn: String::from("metadata/02_type_meta/Detail"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }]);
    println!("{:?}", vec![__ZincTypeMeta { kind: String::from("struct"), name: String::from("Base"), fqn: String::from("metadata/02_type_meta/Base"), family_name: String::from("Base"), family_fqn: String::from("metadata/02_type_meta/Base"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, __ZincTypeMeta { kind: String::from("struct"), name: String::from("Detail"), fqn: String::from("metadata/02_type_meta/Detail"), family_name: String::from("Detail"), family_fqn: String::from("metadata/02_type_meta/Detail"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }]);
    println!("{:?}", __ZincTypeMeta { kind: String::from("enum"), name: String::from("Mode"), fqn: String::from("metadata/02_type_meta/Mode"), family_name: String::from("Mode"), family_fqn: String::from("metadata/02_type_meta/Mode"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() });
    println!("{:?}", Vec::<__ZincFieldMeta>::new());
    println!("{:?}", vec![__ZincMethodMeta { kind: String::from("method"), name: String::from("static_note"), fqn: String::from("metadata/02_type_meta/Mode/static_note"), module_fqn: String::from("metadata/02_type_meta"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/02_type_meta.zn"), line_num: 5, is_public: true, params: Vec::<__ZincMethodParameterMeta>::new(), return_type: __ZincTypeMeta { kind: String::from("primitive"), name: String::from("String"), fqn: String::from("String"), family_name: String::from("String"), family_fqn: String::from("String"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, is_async: false, is_static: true, is_declared: true }]);
    println!("{:?}", vec![__ZincVariantMeta { kind: String::from("variant"), name: String::from("Auto"), fqn: String::from("metadata/02_type_meta/Mode/Auto"), module_fqn: String::from("metadata/02_type_meta"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/02_type_meta.zn"), line_num: 2, is_public: true, index: 0 }, __ZincVariantMeta { kind: String::from("variant"), name: String::from("Manual"), fqn: String::from("metadata/02_type_meta/Mode/Manual"), module_fqn: String::from("metadata/02_type_meta"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/02_type_meta.zn"), line_num: 3, is_public: true, index: 1 }]);
    println!("{:?}", Vec::<__ZincFieldMeta>::new());
    println!("{:?}", Vec::<__ZincMethodMeta>::new());
    println!("{:?}", Vec::<__ZincTypeMeta>::new());
}