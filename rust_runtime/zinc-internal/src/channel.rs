pub enum TryRecv<T> {
    Value(T),
    Empty,
    Closed,
}

pub enum TrySend<T> {
    Sent,
    Full(T),
    Closed(T),
}

enum ChannelSender<T> {
    Bounded(tokio::sync::mpsc::Sender<T>),
    Unbounded(tokio::sync::mpsc::UnboundedSender<T>),
}

enum ChannelReceiver<T> {
    Bounded(tokio::sync::mpsc::Receiver<T>),
    Unbounded(tokio::sync::mpsc::UnboundedReceiver<T>),
}

impl<T> ChannelReceiver<T> {
    async fn recv(&mut self) -> Option<T> {
        match self {
            Self::Bounded(receiver) => receiver.recv().await,
            Self::Unbounded(receiver) => receiver.recv().await,
        }
    }

    fn try_recv(&mut self) -> TryRecv<T> {
        match self {
            Self::Bounded(receiver) => match receiver.try_recv() {
                Ok(value) => TryRecv::Value(value),
                Err(tokio::sync::mpsc::error::TryRecvError::Empty) => TryRecv::Empty,
                Err(tokio::sync::mpsc::error::TryRecvError::Disconnected) => TryRecv::Closed,
            },
            Self::Unbounded(receiver) => match receiver.try_recv() {
                Ok(value) => TryRecv::Value(value),
                Err(tokio::sync::mpsc::error::TryRecvError::Empty) => TryRecv::Empty,
                Err(tokio::sync::mpsc::error::TryRecvError::Disconnected) => TryRecv::Closed,
            },
        }
    }
}

impl<T> Clone for ChannelSender<T> {
    fn clone(&self) -> Self {
        match self {
            Self::Bounded(sender) => Self::Bounded(sender.clone()),
            Self::Unbounded(sender) => Self::Unbounded(sender.clone()),
        }
    }
}

pub struct Channel<T> {
    sender: ChannelSender<T>,
    receiver: std::sync::Arc<tokio::sync::Mutex<ChannelReceiver<T>>>,
    closed: std::sync::Arc<std::sync::atomic::AtomicBool>,
    close_notify: std::sync::Arc<tokio::sync::Notify>,
}

impl<T> Clone for Channel<T> {
    fn clone(&self) -> Self {
        Self {
            sender: self.sender.clone(),
            receiver: self.receiver.clone(),
            closed: self.closed.clone(),
            close_notify: self.close_notify.clone(),
        }
    }
}

impl<T: Send + 'static> Channel<T> {
    pub fn bounded(capacity: i64) -> Self {
        let (sender, receiver) = tokio::sync::mpsc::channel(capacity as usize);
        Self {
            sender: ChannelSender::Bounded(sender),
            receiver: std::sync::Arc::new(tokio::sync::Mutex::new(ChannelReceiver::Bounded(
                receiver,
            ))),
            closed: std::sync::Arc::new(std::sync::atomic::AtomicBool::new(false)),
            close_notify: std::sync::Arc::new(tokio::sync::Notify::new()),
        }
    }

    pub fn unbounded() -> Self {
        let (sender, receiver) = tokio::sync::mpsc::unbounded_channel();
        Self {
            sender: ChannelSender::Unbounded(sender),
            receiver: std::sync::Arc::new(tokio::sync::Mutex::new(ChannelReceiver::Unbounded(
                receiver,
            ))),
            closed: std::sync::Arc::new(std::sync::atomic::AtomicBool::new(false)),
            close_notify: std::sync::Arc::new(tokio::sync::Notify::new()),
        }
    }

    pub async fn send(&self, value: T) {
        if self.closed.load(std::sync::atomic::Ordering::SeqCst) {
            panic!("send on closed channel");
        }
        match &self.sender {
            ChannelSender::Bounded(sender) => {
                if let Err(_) = sender.send(value).await {
                    panic!("send on closed channel");
                }
            }
            ChannelSender::Unbounded(sender) => {
                if let Err(_) = sender.send(value) {
                    panic!("send on closed channel");
                }
            }
        }
    }

    pub fn try_send(&self, value: T) -> TrySend<T> {
        if self.closed.load(std::sync::atomic::Ordering::SeqCst) {
            return TrySend::Closed(value);
        }
        match &self.sender {
            ChannelSender::Bounded(sender) => match sender.try_send(value) {
                Ok(()) => TrySend::Sent,
                Err(tokio::sync::mpsc::error::TrySendError::Full(value)) => TrySend::Full(value),
                Err(tokio::sync::mpsc::error::TrySendError::Closed(value)) => {
                    TrySend::Closed(value)
                }
            },
            ChannelSender::Unbounded(sender) => match sender.send(value) {
                Ok(()) => TrySend::Sent,
                Err(err) => TrySend::Closed(err.0),
            },
        }
    }

    pub fn close(&self) {
        if self.closed.swap(true, std::sync::atomic::Ordering::SeqCst) {
            panic!("double close");
        }
        self.close_notify.notify_waiters();
    }

    pub async fn recv_option(&self) -> Option<T> {
        loop {
            match self.receiver.clone().try_lock_owned() {
                Ok(mut receiver) => match receiver.try_recv() {
                    TryRecv::Value(value) => return Some(value),
                    TryRecv::Closed => return None,
                    TryRecv::Empty => {
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
                    }
                },
                Err(_) => tokio::task::yield_now().await,
            }
        }
    }

    pub async fn recv(&self) -> T {
        match self.recv_option().await {
            Some(value) => value,
            None => panic!("receive on closed channel"),
        }
    }

    pub fn try_recv(&self) -> TryRecv<T> {
        match self.receiver.clone().try_lock_owned() {
            Ok(mut receiver) => match receiver.try_recv() {
                TryRecv::Empty if self.closed.load(std::sync::atomic::Ordering::SeqCst) => {
                    TryRecv::Closed
                }
                result => result,
            },
            Err(_) => TryRecv::Empty,
        }
    }
}
