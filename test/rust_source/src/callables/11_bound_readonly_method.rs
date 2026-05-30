use std::cell::RefCell;
use std::rc::Rc;

#[derive(Clone)]
enum __ZincCallable_Unit_to_i64 {
    Closed,
    V0(Rc<RefCell<callables_11_bound_readonly_method__Counter>>),
}

impl Default for __ZincCallable_Unit_to_i64 {
    fn default() -> Self {
        Self::Closed
    }
}

impl __ZincCallable_Unit_to_i64 {
    fn call(&self, ) -> i64 {
        match self {
            Self::Closed => panic!("callable used after closed receive"),
            Self::V0(receiver) => receiver.borrow().get(),
        }
    }
}

struct callables_11_bound_readonly_method__Counter {
    pub count: i64,
}

impl Default for callables_11_bound_readonly_method__Counter {
    fn default() -> Self {
        Self { count: 7 }
    }
}

impl callables_11_bound_readonly_method__Counter {
    fn get(&self) -> i64 {
        return self.count;
    }
}

fn main() {
    let c = Rc::new(RefCell::new(callables_11_bound_readonly_method__Counter { count: 7 }));
    let step = __ZincCallable_Unit_to_i64::V0(c.clone());
    println!("{}", step.call());
}