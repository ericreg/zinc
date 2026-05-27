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
struct __ZincAnonStruct_AnonStruct_a_i64_b_String_c_bool {
    a: i64,
    b: String,
    c: bool,
}

struct metadata_03_constraints_and_orders__Circle {
    pub name: String,
    pub radius: i64,
}

impl Default for metadata_03_constraints_and_orders__Circle {
    fn default() -> Self {
        Self { name: String::new(), radius: 0 }
    }
}

impl metadata_03_constraints_and_orders__Circle {
    fn area(&self) -> i64 {
        return (self.radius * self.radius);
    }
}

struct metadata_03_constraints_and_orders__Rectangle {
    pub name: String,
    pub width: i64,
}

impl Default for metadata_03_constraints_and_orders__Rectangle {
    fn default() -> Self {
        Self { name: String::new(), width: 0 }
    }
}

impl metadata_03_constraints_and_orders__Rectangle {
    fn area(&self) -> i64 {
        return self.width;
    }
}

struct metadata_03_constraints_and_orders__Shape {
    pub name: String,
}

impl Default for metadata_03_constraints_and_orders__Shape {
    fn default() -> Self {
        Self { name: String::new() }
    }
}

struct metadata_03_constraints_and_orders__Shape2D {
    pub name: String,
}

impl Default for metadata_03_constraints_and_orders__Shape2D {
    fn default() -> Self {
        Self { name: String::new() }
    }
}

impl metadata_03_constraints_and_orders__Shape2D {
    fn area() -> i64 {
        return 0;
    }
}

struct metadata_03_constraints_and_orders__Square {
    pub name: String,
    pub side: i64,
}

impl Default for metadata_03_constraints_and_orders__Square {
    fn default() -> Self {
        Self { name: String::new(), side: 0 }
    }
}

impl metadata_03_constraints_and_orders__Square {
    fn area(&self) -> i64 {
        return (self.side * self.side);
    }
}

// infer-backed struct family metadata_03_constraints_and_orders__Triple uses synthesized concrete shapes

fn metadata_03_constraints_and_orders__accept_nominal_Struct_metadata_03_constraints_and_orders_Circle(shape: metadata_03_constraints_and_orders__Circle) {
    println!("{:?}", __ZincFunctionParameterMeta { kind: String::from("parameter"), name: String::from("shape"), fqn: String::from("metadata/03_constraints_and_orders/accept_nominal/shape"), module_fqn: String::from("metadata/03_constraints_and_orders"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/03_constraints_and_orders.zn"), line_num: 48, is_public: false, index: 0, value_type: __ZincTypeMeta { kind: String::from("struct"), name: String::from("Circle"), fqn: String::from("metadata/03_constraints_and_orders/Circle"), family_name: String::from("Circle"), family_fqn: String::from("metadata/03_constraints_and_orders/Circle"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, declared_type: __ZincTypeMeta { kind: String::from("unknown"), name: String::from("unknown"), fqn: String::from("unknown"), family_name: String::from("unknown"), family_fqn: String::from("unknown"), args: Vec::<__ZincTypeMeta>::new(), is_named: false, is_bounded: false, infer_slots: Vec::<String>::new() }, has_declared_type: false });
    println!("{:?}", __ZincTypeMeta { kind: String::from("struct"), name: String::from("Circle"), fqn: String::from("metadata/03_constraints_and_orders/Circle"), family_name: String::from("Circle"), family_fqn: String::from("metadata/03_constraints_and_orders/Circle"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() });
    println!("{}", shape.area());
}

fn metadata_03_constraints_and_orders__accept_nominal_Struct_metadata_03_constraints_and_orders_Square(shape: metadata_03_constraints_and_orders__Square) {
    println!("{:?}", __ZincFunctionParameterMeta { kind: String::from("parameter"), name: String::from("shape"), fqn: String::from("metadata/03_constraints_and_orders/accept_nominal/shape"), module_fqn: String::from("metadata/03_constraints_and_orders"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/03_constraints_and_orders.zn"), line_num: 48, is_public: false, index: 0, value_type: __ZincTypeMeta { kind: String::from("struct"), name: String::from("Square"), fqn: String::from("metadata/03_constraints_and_orders/Square"), family_name: String::from("Square"), family_fqn: String::from("metadata/03_constraints_and_orders/Square"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, declared_type: __ZincTypeMeta { kind: String::from("unknown"), name: String::from("unknown"), fqn: String::from("unknown"), family_name: String::from("unknown"), family_fqn: String::from("unknown"), args: Vec::<__ZincTypeMeta>::new(), is_named: false, is_bounded: false, infer_slots: Vec::<String>::new() }, has_declared_type: false });
    println!("{:?}", __ZincTypeMeta { kind: String::from("struct"), name: String::from("Square"), fqn: String::from("metadata/03_constraints_and_orders/Square"), family_name: String::from("Square"), family_fqn: String::from("metadata/03_constraints_and_orders/Square"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() });
    println!("{}", shape.area());
}

fn metadata_03_constraints_and_orders__accept_structural_Struct_metadata_03_constraints_and_orders_Rectangle(shape: metadata_03_constraints_and_orders__Rectangle) {
    println!("{:?}", __ZincFunctionParameterMeta { kind: String::from("parameter"), name: String::from("shape"), fqn: String::from("metadata/03_constraints_and_orders/accept_structural/shape"), module_fqn: String::from("metadata/03_constraints_and_orders"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/03_constraints_and_orders.zn"), line_num: 55, is_public: false, index: 0, value_type: __ZincTypeMeta { kind: String::from("struct"), name: String::from("Rectangle"), fqn: String::from("metadata/03_constraints_and_orders/Rectangle"), family_name: String::from("Rectangle"), family_fqn: String::from("metadata/03_constraints_and_orders/Rectangle"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, declared_type: __ZincTypeMeta { kind: String::from("unknown"), name: String::from("unknown"), fqn: String::from("unknown"), family_name: String::from("unknown"), family_fqn: String::from("unknown"), args: Vec::<__ZincTypeMeta>::new(), is_named: false, is_bounded: false, infer_slots: Vec::<String>::new() }, has_declared_type: false });
    println!("{:?}", __ZincTypeMeta { kind: String::from("struct"), name: String::from("Rectangle"), fqn: String::from("metadata/03_constraints_and_orders/Rectangle"), family_name: String::from("Rectangle"), family_fqn: String::from("metadata/03_constraints_and_orders/Rectangle"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() });
    println!("{}", shape.area());
}

fn main() {
    let triple = __ZincAnonStruct_AnonStruct_a_i64_b_String_c_bool { a: 9, b: String::from("ok"), c: true };
    let circle = metadata_03_constraints_and_orders__Circle { name: String::from("circle"), radius: 4 };
    let square = metadata_03_constraints_and_orders__Square { name: String::from("square"), side: 3 };
    let rect = metadata_03_constraints_and_orders__Rectangle { name: String::from("rect"), width: 5 };
    println!("{}", 67);
    println!("{:?}", __ZincStructMeta { kind: String::from("struct"), name: String::from("Triple"), fqn: String::from("metadata/03_constraints_and_orders/Triple"), module_fqn: String::from("metadata/03_constraints_and_orders"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/03_constraints_and_orders.zn"), line_num: 36, is_public: true, type_info: __ZincTypeMeta { kind: String::from("struct"), name: String::from("Triple"), fqn: String::from("metadata/03_constraints_and_orders/Triple"), family_name: String::from("Triple"), family_fqn: String::from("metadata/03_constraints_and_orders/Triple"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: vec![String::from("a"), String::from("b"), String::from("c")] } });
    println!("{:?}", __ZincTypeMeta { kind: String::from("struct"), name: String::from("Triple<i64, String, bool>"), fqn: String::from("metadata/03_constraints_and_orders/Triple<i64, String, bool>"), family_name: String::from("Triple"), family_fqn: String::from("metadata/03_constraints_and_orders/Triple"), args: vec![__ZincTypeMeta { kind: String::from("primitive"), name: String::from("i64"), fqn: String::from("i64"), family_name: String::from("i64"), family_fqn: String::from("i64"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, __ZincTypeMeta { kind: String::from("primitive"), name: String::from("String"), fqn: String::from("String"), family_name: String::from("String"), family_fqn: String::from("String"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, __ZincTypeMeta { kind: String::from("primitive"), name: String::from("bool"), fqn: String::from("bool"), family_name: String::from("bool"), family_fqn: String::from("bool"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }], is_named: true, is_bounded: false, infer_slots: vec![String::from("a"), String::from("b"), String::from("c")] });
    println!("{}", true);
    println!("{}", false);
    println!("{}", true);
    println!("{}", true);
    println!("{}", false);
    metadata_03_constraints_and_orders__accept_nominal_Struct_metadata_03_constraints_and_orders_Circle(circle);
    metadata_03_constraints_and_orders__accept_nominal_Struct_metadata_03_constraints_and_orders_Square(square);
    metadata_03_constraints_and_orders__accept_structural_Struct_metadata_03_constraints_and_orders_Rectangle(rect);
    println!("{:?}", vec![__ZincTypeMeta { kind: String::from("struct"), name: String::from("Shape2D"), fqn: String::from("metadata/03_constraints_and_orders/Shape2D"), family_name: String::from("Shape2D"), family_fqn: String::from("metadata/03_constraints_and_orders/Shape2D"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, __ZincTypeMeta { kind: String::from("struct"), name: String::from("Shape"), fqn: String::from("metadata/03_constraints_and_orders/Shape"), family_name: String::from("Shape"), family_fqn: String::from("metadata/03_constraints_and_orders/Shape"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }]);
    println!("{:?}", vec![__ZincTypeMeta { kind: String::from("struct"), name: String::from("Shape"), fqn: String::from("metadata/03_constraints_and_orders/Shape"), family_name: String::from("Shape"), family_fqn: String::from("metadata/03_constraints_and_orders/Shape"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, __ZincTypeMeta { kind: String::from("struct"), name: String::from("Shape2D"), fqn: String::from("metadata/03_constraints_and_orders/Shape2D"), family_name: String::from("Shape2D"), family_fqn: String::from("metadata/03_constraints_and_orders/Shape2D"), args: Vec::<__ZincTypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }]);
}