struct structs_13_base_types__BaseTypes {
    pub signed8: i8,
    pub signed16: i16,
    pub signed32: i32,
    pub signed64: i64,
    pub signed128: i128,
    pub unsigned8: u8,
    pub unsigned16: u16,
    pub unsigned32: u32,
    pub unsigned64: u64,
    pub unsigned128: u128,
    pub float32: f32,
    pub float64: f64,
    pub text: String,
    pub flag: bool,
}

impl Default for structs_13_base_types__BaseTypes {
    fn default() -> Self {
        Self { signed8: 0, signed16: 0, signed32: 0, signed64: 0, signed128: 0, unsigned8: 0, unsigned16: 0, unsigned32: 0, unsigned64: 0, unsigned128: 0, float32: 0.0, float64: 0.0, text: String::new(), flag: false }
    }
}

impl structs_13_base_types__BaseTypes {
    fn new(signed8: i8, signed16: i16, signed32: i32, signed64: i64, signed128: i128, unsigned8: u8, unsigned16: u16, unsigned32: u32, unsigned64: u64, unsigned128: u128, float32: f32, float64: f64, text: String, flag: bool) -> Self {
        return structs_13_base_types__BaseTypes { signed8: signed8, signed16: signed16, signed32: signed32, signed64: signed64, signed128: signed128, unsigned8: unsigned8, unsigned16: unsigned16, unsigned32: unsigned32, unsigned64: unsigned64, unsigned128: unsigned128, float32: float32, float64: float64, text: text, flag: flag };
    }
    fn signed8_value(&self) -> i8 {
        return self.signed8;
    }
    fn unsigned128_value(&self) -> u128 {
        return self.unsigned128;
    }
    fn float32_value(&self) -> f32 {
        return self.float32;
    }
    fn float64_value(&self) -> f64 {
        return self.float64;
    }
    fn flag_value(&self) -> bool {
        return self.flag;
    }
}

fn main() {
    let values = structs_13_base_types__BaseTypes::new((-8), (-16), (-32), (-64), (-128), 8, 16, 32, 64, 128, 3.25, 6.5, String::from("hello"), true);
    println!("{}", values.signed8);
    println!("{}", values.signed16);
    println!("{}", values.signed32);
    println!("{}", values.signed64);
    println!("{}", values.signed128);
    println!("{}", values.unsigned8);
    println!("{}", values.unsigned16);
    println!("{}", values.unsigned32);
    println!("{}", values.unsigned64);
    println!("{}", values.unsigned128);
    println!("{}", values.float32);
    println!("{}", values.float64);
    println!("{}", values.text);
    println!("{}", values.flag);
    println!("{}", values.signed8_value());
    println!("{}", values.unsigned128_value());
    println!("{}", values.float32_value());
    println!("{}", values.float64_value());
    println!("{}", values.flag_value());
}