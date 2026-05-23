struct structs_11_composition_static_methods__File {
    pub path: String,
}

impl structs_11_composition_static_methods__File {
    fn new(path: String) -> Self {
        return structs_11_composition_static_methods__File { path: path };
    }
    fn kind() -> i64 {
        return 1;
    }
}

struct structs_11_composition_static_methods__Item {
    pub path: String,
    pub text: String,
    pub timestamp: i64,
}

impl structs_11_composition_static_methods__Item {
    fn new(path: String) -> Self {
        return structs_11_composition_static_methods__Item { path: path, text: String::new(), timestamp: 0 };
    }
    fn kind() -> i64 {
        return 1;
    }
    fn with_text(text: String) -> Self {
        return structs_11_composition_static_methods__Item { path: String::new(), text: text, timestamp: 0 };
    }
}

struct structs_11_composition_static_methods__Message {
    pub text: String,
    pub timestamp: i64,
}

impl structs_11_composition_static_methods__Message {
    fn with_text(text: String) -> Self {
        return structs_11_composition_static_methods__Message { text: text, timestamp: 0 };
    }
}

fn main() {
    let from_file = structs_11_composition_static_methods__Item::new(String::from("/tmp/log.txt"));
    println!("{}", from_file.path);
    println!("{}", from_file.text);
    println!("{}", from_file.timestamp);
    let from_message = structs_11_composition_static_methods__Item::with_text(String::from("hello"));
    println!("{}", from_message.path);
    println!("{}", from_message.text);
    println!("{}", from_message.timestamp);
    println!("{}", structs_11_composition_static_methods__Item::kind());
}