struct MyStruct {
    _called: bool,
    pub a: i64,
    pub b: String,
    pub c: i64,
    pub d: i64,
    pub e: f64,
}

impl MyStruct {
    fn new(a: i32, b: String) -> Self {
        return MyStruct {
            a: a,
            b: b,
            _called: true,
        };
    }

    fn get_value() -> i64 {
        return 5;
    }

    fn increment(&mut self) {
        self.c = self.c + Self::get_value();
    }

    fn to_string(&self) -> String {
        return format!("MyStruct(a: {}, b: {}, c: {}, d: {})", self.a, self.b, self.c, self.d);
    }

}
fn main() {
    let my_struct = MyStruct {
        _called: false,
        a: 5,
        b: String::from("3"),
        c: 10,
        d: 20,
        e: 0.0,
    };
    let your_struct = MyStruct {
        _called: false,
        a: 5,
        b: String::from("3"),
        c: 10,
        d: 20,
        e: 0.0,
    };
    let another_struct = MyStruct {
        _called: false,
        a: 5,
        b: String::from("3"),
        c: 10,
        d: 20,
        e: 0.0,
    };
    let another_struct = MyStruct::new(3, String::from("5"));
    another_struct.increment();
    let increment_value_static = MyStruct::get_value();
    let increment_value_static = my_struct.get_value();
}
