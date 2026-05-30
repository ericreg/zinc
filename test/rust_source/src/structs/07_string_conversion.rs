struct structs_07_string_conversion__Greeting {
    pub text: String,
}

impl Default for structs_07_string_conversion__Greeting {
    fn default() -> Self {
        Self { text: String::new() }
    }
}

impl structs_07_string_conversion__Greeting {
    fn new(text: String) -> Self {
        return structs_07_string_conversion__Greeting { text: text };
    }
}

struct structs_07_string_conversion__Message {
    pub content: String,
    pub sender: String,
    pub priority: i32,
}

impl Default for structs_07_string_conversion__Message {
    fn default() -> Self {
        Self { content: String::new(), sender: String::new(), priority: 0 }
    }
}

impl structs_07_string_conversion__Message {
    fn new(content: String, sender: String) -> Self {
        return structs_07_string_conversion__Message { content: content, sender: sender, priority: 0 };
    }
    fn with_priority(content: String, sender: String, priority: i32) -> Self {
        return structs_07_string_conversion__Message { content: content, sender: sender, priority: priority };
    }
}

fn main() {
    let msg1 = structs_07_string_conversion__Message { content: String::from("Hello World"), sender: String::from("Alice"), priority: 1 };
    println!("{}", msg1.content);
    println!("{}", msg1.sender);
    let msg2 = structs_07_string_conversion__Message::new(String::from("Test message"), String::from("Bob"));
    println!("{}", msg2.content);
    println!("{}", msg2.sender);
    let msg3 = structs_07_string_conversion__Message::with_priority(String::from("Urgent"), String::from("Admin"), (10) as i32);
    println!("{}", msg3.content);
    println!("{}", msg3.priority);
    let greeting = structs_07_string_conversion__Greeting::new(String::from("Welcome!"));
    println!("{}", greeting.text);
}