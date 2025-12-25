struct Counter {
    pub count: i64,
    pub step: i64,
}

impl Counter {
    fn get_count(&self) -> i64 {
        return self.count;
    }
    fn get_step(&self) -> i64 {
        return self.step;
    }
    fn increment(&mut self) {
        self.count = (self.count + self.step);
    }
    fn reset(&mut self) {
        self.count = 0;
    }
    fn set_step(&mut self, new_step: i64) {
        self.step = new_step;
    }
    fn new(initial: i64, step: i64) -> Self {
        return Counter { count: initial, step: step };
    }
}

fn main() {
    let mut counter = Counter::new(0, 5);
    println!("{}", counter.get_count());
    counter.increment();
    println!("{}", counter.get_count());
    counter.increment();
    println!("{}", counter.get_count());
    counter.set_step(10);
    counter.increment();
    println!("{}", counter.get_count());
    counter.reset();
    println!("{}", counter.get_count());
}