use crate::Channel;

#[derive(Clone)]
pub struct Context {
    done: Channel<bool>,
}

impl Default for Context {
    fn default() -> Self {
        Self::background()
    }
}

impl Context {
    pub fn background() -> Self {
        Self {
            done: Channel::unbounded(),
        }
    }

    pub fn done(&self) -> Channel<bool> {
        self.done.clone()
    }

    pub fn cancel(&self) {
        self.done.close();
    }
}
