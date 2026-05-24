use std::cell::RefCell;
use std::rc::Rc;

#[derive(Clone)]
enum __ZincCallable_Unit_to_unknown {
    V0(Rc<RefCell<callables_03_bound_method__Counter>>),
}

impl __ZincCallable_Unit_to_unknown {
    fn call(&self, ) {
        match self {
            Self::V0(receiver) => { receiver.borrow_mut().inc(); }
        }
    }
}

struct callables_03_bound_method__Counter {
    pub count: i64,
}

impl callables_03_bound_method__Counter {
    fn inc(&mut self) {
        self.count = (self.count + 1);
    }
    fn get(&self) -> i64 {
        return self.count;
    }
}

fn main() {
    let c = Rc::new(RefCell::new(callables_03_bound_method__Counter { count: 0 }));
    let step = __ZincCallable_Unit_to_unknown::V0(c.clone());
    step.call();
    println!("{}", c.borrow().get());
}