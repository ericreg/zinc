use crate::__ZincChannel;

#[derive(Clone)]
pub struct __ZincContext {
    done: __ZincChannel<bool>,
}

impl Default for __ZincContext {
    fn default() -> Self {
        Self::background()
    }
}

impl __ZincContext {
    pub fn background() -> Self {
        Self { done: __ZincChannel::unbounded() }
    }

    pub fn done(&self) -> __ZincChannel<bool> {
        self.done.clone()
    }

    pub fn cancel(&self) {
        self.done.close();
    }
}
