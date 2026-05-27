static METADATA_01_SYMBOL_META__APP_NAME: std::sync::LazyLock<String> = std::sync::LazyLock::new(|| String::from("zinc"));

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

#[derive(Clone)]
enum metadata_01_symbol_meta__Status {
    Ready,
    Busy,
}

impl metadata_01_symbol_meta__Status {
    fn banner(prefix: String) -> String {
        return format!("{}:status", prefix);
    }
}

struct metadata_01_symbol_meta__Profile {
    pub version: i64,
    pub name: String,
}

impl Default for metadata_01_symbol_meta__Profile {
    fn default() -> Self {
        Self { version: 1, name: String::new() }
    }
}

impl metadata_01_symbol_meta__Profile {
    fn label(&self, prefix: String) -> String {
        return format!("{}:{}:{}", prefix, self.name, (*METADATA_01_SYMBOL_META__APP_NAME).clone());
    }
    fn build_tag(suffix: String) -> String {
        return format!("{}:build", suffix);
    }
}

fn metadata_01_symbol_meta__inspect_i64(count: i64) -> i64 {
    let local = count;
    let typed: String = (*METADATA_01_SYMBOL_META__APP_NAME).clone();
    println!("{}", 32);
    println!("{:?}", __ZincFunctionParameterMeta { kind: String::from("parameter"), name: String::from("count"), fqn: String::from("metadata/01_symbol_meta/inspect/count"), module_fqn: String::from("metadata/01_symbol_meta"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/01_symbol_meta.zn"), line_num: 29, is_public: false, index: 0, value_type: __ZincTypeMeta { kind: String::from("primitive"), name: String::from("i64"), fqn: String::from("i64"), family_name: String::from("i64"), family_fqn: String::from("i64"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, declared_type: __ZincTypeMeta { kind: String::from("primitive"), name: String::from("i64"), fqn: String::from("i64"), family_name: String::from("i64"), family_fqn: String::from("i64"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, has_declared_type: true });
    println!("{}", String::from("inspect"));
    println!("{}", String::from("i64"));
    println!("{:?}", __ZincVariableMeta { kind: String::from("variable"), name: String::from("local"), fqn: String::from("metadata/01_symbol_meta/inspect/local"), module_fqn: String::from("metadata/01_symbol_meta"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/01_symbol_meta.zn"), line_num: 30, is_public: false, value_type: __ZincTypeMeta { kind: String::from("primitive"), name: String::from("i64"), fqn: String::from("i64"), family_name: String::from("i64"), family_fqn: String::from("i64"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, has_declared_type: false, is_mutated: false, is_shadow: false });
    println!("{}", String::from("inspect"));
    println!("{}", String::from("i64"));
    println!("{}", true);
    println!("{:?}", __ZincConstMeta { kind: String::from("const"), name: String::from("APP_NAME"), fqn: String::from("metadata/01_symbol_meta/APP_NAME"), module_fqn: String::from("metadata/01_symbol_meta"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/01_symbol_meta.zn"), line_num: 1, is_public: true, value_type: __ZincTypeMeta { kind: String::from("primitive"), name: String::from("String"), fqn: String::from("String"), family_name: String::from("String"), family_fqn: String::from("String"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, value_text: String::from("\"zinc\"") });
    println!("{:?}", __ZincFunctionMeta { kind: String::from("function"), name: String::from("inspect"), fqn: String::from("metadata/01_symbol_meta/inspect"), module_fqn: String::from("metadata/01_symbol_meta"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/01_symbol_meta.zn"), line_num: 29, is_public: true, params: vec![__ZincFunctionParameterMeta { kind: String::from("parameter"), name: String::from("count"), fqn: String::from("metadata/01_symbol_meta/inspect/count"), module_fqn: String::from("metadata/01_symbol_meta"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/01_symbol_meta.zn"), line_num: 29, is_public: false, index: 0, value_type: __ZincTypeMeta { kind: String::from("primitive"), name: String::from("i64"), fqn: String::from("i64"), family_name: String::from("i64"), family_fqn: String::from("i64"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, declared_type: __ZincTypeMeta { kind: String::from("primitive"), name: String::from("i64"), fqn: String::from("i64"), family_name: String::from("i64"), family_fqn: String::from("i64"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, has_declared_type: true }], return_type: __ZincTypeMeta { kind: String::from("primitive"), name: String::from("i64"), fqn: String::from("i64"), family_name: String::from("i64"), family_fqn: String::from("i64"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, is_async: false });
    println!("{:?}", __ZincFunctionParameterMeta { kind: String::from("parameter"), name: String::from("count"), fqn: String::from("metadata/01_symbol_meta/inspect/count"), module_fqn: String::from("metadata/01_symbol_meta"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/01_symbol_meta.zn"), line_num: 29, is_public: false, index: 0, value_type: __ZincTypeMeta { kind: String::from("primitive"), name: String::from("i64"), fqn: String::from("i64"), family_name: String::from("i64"), family_fqn: String::from("i64"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, declared_type: __ZincTypeMeta { kind: String::from("primitive"), name: String::from("i64"), fqn: String::from("i64"), family_name: String::from("i64"), family_fqn: String::from("i64"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, has_declared_type: true });
    println!("{}", String::from("inspect"));
    println!("{:?}", __ZincTypeMeta { kind: String::from("primitive"), name: String::from("i64"), fqn: String::from("i64"), family_name: String::from("i64"), family_fqn: String::from("i64"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() });
    println!("{:?}", __ZincFunctionMeta { kind: String::from("function"), name: String::from("ping"), fqn: String::from("metadata/01_symbol_meta/ping"), module_fqn: String::from("metadata/01_symbol_meta"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/01_symbol_meta.zn"), line_num: 25, is_public: true, params: Vec::<__ZincFunctionParameterMeta>::new(), return_type: __ZincTypeMeta { kind: String::from("unknown"), name: String::from("unknown"), fqn: String::from("unknown"), family_name: String::from("unknown"), family_fqn: String::from("unknown"), args: Vec::<__ZincTypeMeta>::new(), is_named: false, is_bounded: false, infer_slots: Vec::<String>::new() }, is_async: true });
    println!("{:?}", __ZincBuiltinMeta { kind: String::from("builtin"), name: String::from("print"), fqn: String::from("builtin/print"), module_fqn: String::from("builtin"), file: String::from(""), line_num: 0, is_public: true, params: Vec::<__ZincFunctionParameterMeta>::new(), return_type: __ZincTypeMeta { kind: String::from("primitive"), name: String::from("()"), fqn: String::from("()"), family_name: String::from("()"), family_fqn: String::from("()"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, is_async: false });
    return count;
}

#[tokio::main]
async fn main() {
    let profile = metadata_01_symbol_meta__Profile { version: 1, name: String::from("Ada") };
    let queue = __ZincChannel::<i64>::bounded(1);
    queue.send(11).await;
    println!("{:?}", __ZincStructMeta { kind: String::from("struct"), name: String::from("Profile"), fqn: String::from("metadata/01_symbol_meta/Profile"), module_fqn: String::from("metadata/01_symbol_meta"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/01_symbol_meta.zn"), line_num: 12, is_public: true, type_info: __ZincTypeMeta { kind: String::from("struct"), name: String::from("Profile"), fqn: String::from("metadata/01_symbol_meta/Profile"), family_name: String::from("Profile"), family_fqn: String::from("metadata/01_symbol_meta/Profile"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() } });
    println!("{:?}", __ZincTypeMeta { kind: String::from("struct"), name: String::from("Profile"), fqn: String::from("metadata/01_symbol_meta/Profile"), family_name: String::from("Profile"), family_fqn: String::from("metadata/01_symbol_meta/Profile"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() });
    println!("{:?}", vec![__ZincFieldMeta { kind: String::from("field"), name: String::from("version"), fqn: String::from("metadata/01_symbol_meta/Profile/version"), module_fqn: String::from("metadata/01_symbol_meta"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/01_symbol_meta.zn"), line_num: 13, is_public: true, value_type: __ZincTypeMeta { kind: String::from("primitive"), name: String::from("i64"), fqn: String::from("i64"), family_name: String::from("i64"), family_fqn: String::from("i64"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, index: 0, is_const: true, has_default: true, is_declared: true, source_component_fqn: String::from("") }, __ZincFieldMeta { kind: String::from("field"), name: String::from("name"), fqn: String::from("metadata/01_symbol_meta/Profile/name"), module_fqn: String::from("metadata/01_symbol_meta"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/01_symbol_meta.zn"), line_num: 14, is_public: true, value_type: __ZincTypeMeta { kind: String::from("primitive"), name: String::from("String"), fqn: String::from("String"), family_name: String::from("String"), family_fqn: String::from("String"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, index: 1, is_const: false, has_default: false, is_declared: true, source_component_fqn: String::from("") }]);
    println!("{:?}", __ZincEnumMeta { kind: String::from("enum"), name: String::from("Status"), fqn: String::from("metadata/01_symbol_meta/Status"), module_fqn: String::from("metadata/01_symbol_meta"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/01_symbol_meta.zn"), line_num: 3, is_public: true, type_info: __ZincTypeMeta { kind: String::from("enum"), name: String::from("Status"), fqn: String::from("metadata/01_symbol_meta/Status"), family_name: String::from("Status"), family_fqn: String::from("metadata/01_symbol_meta/Status"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() } });
    println!("{:?}", __ZincTypeMeta { kind: String::from("enum"), name: String::from("Status"), fqn: String::from("metadata/01_symbol_meta/Status"), family_name: String::from("Status"), family_fqn: String::from("metadata/01_symbol_meta/Status"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() });
    println!("{:?}", vec![__ZincVariantMeta { kind: String::from("variant"), name: String::from("Ready"), fqn: String::from("metadata/01_symbol_meta/Status/Ready"), module_fqn: String::from("metadata/01_symbol_meta"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/01_symbol_meta.zn"), line_num: 4, is_public: true, index: 0 }, __ZincVariantMeta { kind: String::from("variant"), name: String::from("Busy"), fqn: String::from("metadata/01_symbol_meta/Status/Busy"), module_fqn: String::from("metadata/01_symbol_meta"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/01_symbol_meta.zn"), line_num: 5, is_public: true, index: 1 }]);
    println!("{:?}", __ZincVariantMeta { kind: String::from("variant"), name: String::from("Ready"), fqn: String::from("metadata/01_symbol_meta/Status/Ready"), module_fqn: String::from("metadata/01_symbol_meta"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/01_symbol_meta.zn"), line_num: 4, is_public: true, index: 0 });
    println!("{}", String::from("Status"));
    println!("{:?}", __ZincMethodMeta { kind: String::from("method"), name: String::from("build_tag"), fqn: String::from("metadata/01_symbol_meta/Profile/build_tag"), module_fqn: String::from("metadata/01_symbol_meta"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/01_symbol_meta.zn"), line_num: 20, is_public: true, params: vec![__ZincMethodParameterMeta { kind: String::from("parameter"), name: String::from("suffix"), fqn: String::from("metadata/01_symbol_meta/Profile/build_tag/suffix"), module_fqn: String::from("metadata/01_symbol_meta"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/01_symbol_meta.zn"), line_num: 20, is_public: false, index: 0, value_type: __ZincTypeMeta { kind: String::from("primitive"), name: String::from("String"), fqn: String::from("String"), family_name: String::from("String"), family_fqn: String::from("String"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, declared_type: __ZincTypeMeta { kind: String::from("primitive"), name: String::from("String"), fqn: String::from("String"), family_name: String::from("String"), family_fqn: String::from("String"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, has_declared_type: true }], return_type: __ZincTypeMeta { kind: String::from("primitive"), name: String::from("String"), fqn: String::from("String"), family_name: String::from("String"), family_fqn: String::from("String"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, is_async: false, is_static: true, is_declared: true });
    println!("{:?}", __ZincMethodParameterMeta { kind: String::from("parameter"), name: String::from("suffix"), fqn: String::from("metadata/01_symbol_meta/Profile/build_tag/suffix"), module_fqn: String::from("metadata/01_symbol_meta"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/01_symbol_meta.zn"), line_num: 20, is_public: false, index: 0, value_type: __ZincTypeMeta { kind: String::from("primitive"), name: String::from("String"), fqn: String::from("String"), family_name: String::from("String"), family_fqn: String::from("String"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, declared_type: __ZincTypeMeta { kind: String::from("primitive"), name: String::from("String"), fqn: String::from("String"), family_name: String::from("String"), family_fqn: String::from("String"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, has_declared_type: true });
    println!("{:?}", __ZincFieldMeta { kind: String::from("field"), name: String::from("name"), fqn: String::from("metadata/01_symbol_meta/Profile/name"), module_fqn: String::from("metadata/01_symbol_meta"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/01_symbol_meta.zn"), line_num: 14, is_public: true, value_type: __ZincTypeMeta { kind: String::from("primitive"), name: String::from("String"), fqn: String::from("String"), family_name: String::from("String"), family_fqn: String::from("String"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, index: 1, is_const: false, has_default: false, is_declared: true, source_component_fqn: String::from("") });
    println!("{}", String::from("Profile"));
    println!("{:?}", __ZincMethodMeta { kind: String::from("method"), name: String::from("label"), fqn: String::from("metadata/01_symbol_meta/Profile/label"), module_fqn: String::from("metadata/01_symbol_meta"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/01_symbol_meta.zn"), line_num: 16, is_public: true, params: vec![__ZincMethodParameterMeta { kind: String::from("parameter"), name: String::from("prefix"), fqn: String::from("metadata/01_symbol_meta/Profile/label/prefix"), module_fqn: String::from("metadata/01_symbol_meta"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/01_symbol_meta.zn"), line_num: 16, is_public: false, index: 0, value_type: __ZincTypeMeta { kind: String::from("primitive"), name: String::from("String"), fqn: String::from("String"), family_name: String::from("String"), family_fqn: String::from("String"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, declared_type: __ZincTypeMeta { kind: String::from("primitive"), name: String::from("String"), fqn: String::from("String"), family_name: String::from("String"), family_fqn: String::from("String"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, has_declared_type: true }], return_type: __ZincTypeMeta { kind: String::from("primitive"), name: String::from("String"), fqn: String::from("String"), family_name: String::from("String"), family_fqn: String::from("String"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, is_async: false, is_static: false, is_declared: true });
    println!("{}", String::from("Profile"));
    println!("{:?}", __ZincVariableMeta { kind: String::from("variable"), name: String::from("queue"), fqn: String::from("metadata/01_symbol_meta/main/queue"), module_fqn: String::from("metadata/01_symbol_meta"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/01_symbol_meta.zn"), line_num: 52, is_public: false, value_type: __ZincTypeMeta { kind: String::from("channel"), name: String::from("channel<i64>"), fqn: String::from("channel<i64>"), family_name: String::from("channel"), family_fqn: String::from("channel"), args: vec![__ZincTypeMeta { kind: String::from("primitive"), name: String::from("i64"), fqn: String::from("i64"), family_name: String::from("i64"), family_fqn: String::from("i64"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }], is_named: false, is_bounded: true, infer_slots: Vec::<String>::new() }, has_declared_type: false, is_mutated: false, is_shadow: false });
    println!("{:?}", __ZincTypeMeta { kind: String::from("channel"), name: String::from("channel<i64>"), fqn: String::from("channel<i64>"), family_name: String::from("channel"), family_fqn: String::from("channel"), args: vec![__ZincTypeMeta { kind: String::from("primitive"), name: String::from("i64"), fqn: String::from("i64"), family_name: String::from("i64"), family_fqn: String::from("i64"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }], is_named: false, is_bounded: true, infer_slots: Vec::<String>::new() });
    println!("{}", String::from("i64"));
    println!("{}", true);
    println!("{}", String::from("builtin/type"));
    println!("{}", metadata_01_symbol_meta__inspect_i64(5));
    println!("{}", profile.label(String::from("hi")));
    println!("{}", metadata_01_symbol_meta__Profile::build_tag(String::from("prod")));
    println!("{}", metadata_01_symbol_meta__Status::banner((*METADATA_01_SYMBOL_META__APP_NAME).clone()));
}