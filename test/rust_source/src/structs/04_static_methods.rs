struct Calculator {
    pub value: i32,
}

impl Calculator {
    fn pi() -> i64 {
        return 3;
    }
    fn new(initial: i32) -> Self {
        return Calculator { value: initial };
    }
    fn zero() -> Self {
        return Calculator { value: 0 };
    }
}

fn main() {
    let pi_value = Calculator::pi();
    println!("{}", pi_value);
    let calc = Calculator::new((100) as i32);
    println!("{}", calc.value);
    let zero_calc = Calculator::zero();
    println!("{}", zero_calc.value);
}