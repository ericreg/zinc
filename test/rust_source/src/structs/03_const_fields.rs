struct Config {
    pub max_retries: i64,
    pub timeout: i64,
    pub api_version: String,
    pub name: String,
}

struct Circle {
    pub pi: f64,
    pub radius: f64,
}

fn main() {
    let cfg = Config {
        max_retries: 3,
        timeout: 30,
        api_version: String::from("v1.0"),
        name: String::from("my_app"),
    };
    println!("cfg.max_retries");
    println!("cfg.timeout");
    let circle = Circle {
        pi: 3.14159,
        radius: 5.0,
    };
    println!("circle.radius");
}
