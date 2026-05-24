use std::cell::RefCell;
use std::rc::Rc;

#[derive(Clone)]
enum __ZincCallable_Unit_to_i64 {
    V0(Rc<RefCell<callables_11_bound_readonly_method__Counter>>),
}

impl __ZincCallable_Unit_to_i64 {
    fn call(&self, ) -> i64 {
        match self {
            Self::V0(receiver) => receiver.borrow().get(),
        }
    }
}

struct callables_11_bound_readonly_method__Counter {
    pub count: i64,
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