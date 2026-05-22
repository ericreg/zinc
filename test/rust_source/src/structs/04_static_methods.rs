struct structs_04_static_methods__Calculator {
    pub value: i32,
}

impl structs_04_static_methods__Calculator {
    fn pi() -> i64 {
        return 3;
    }
    fn new(initial: i32) -> Self {
        return structs_04_static_methods__Calculator { value: initial };
    }
    fn zero() -> Self {
        return structs_04_static_methods__Calculator { value: 0 };
    }
}

fn main() {
    let pi_value = structs_04_static_methods__Calculator::pi();
    println!("{}", pi_value);
    let calc = structs_04_static_methods__Calculator::new((100) as i32);
    println!("{}", calc.value);
    let zero_calc = structs_04_static_methods__Calculator::zero();
    println!("{}", zero_calc.value);
}