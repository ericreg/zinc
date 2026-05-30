struct structs_03_const_fields__Circle {
    pub pi: f64,
    pub radius: f64,
}

impl Default for structs_03_const_fields__Circle {
    fn default() -> Self {
        Self { pi: 3.14159, radius: 0.0 }
    }
}

struct structs_03_const_fields__Config {
    pub max_retries: i64,
    pub timeout: i64,
    pub api_version: String,
    pub name: String,
}

impl Default for structs_03_const_fields__Config {
    fn default() -> Self {
        Self { max_retries: 3, timeout: 30, api_version: String::new(), name: String::new() }
    }
}

fn main() {
    let cfg = structs_03_const_fields__Config { max_retries: 3, timeout: 30, api_version: String::from("v1.0"), name: String::from("my_app") };
    println!("{}", cfg.max_retries);
    println!("{}", cfg.timeout);
    let circle = structs_03_const_fields__Circle { pi: 3.14159, radius: 5.0 };
    println!("{}", circle.radius);
}