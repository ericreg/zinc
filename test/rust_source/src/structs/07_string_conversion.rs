struct Greeting {
    pub text: String,
}

impl Greeting {
    fn new(text: String) -> Self {
        return Greeting { text: text };
    }
}

struct Message {
    pub content: String,
    pub sender: String,
    pub priority: i32,
}

impl Message {
    fn new(content: String, sender: String) -> Self {
        return Message { content: content, sender: sender, priority: 0 };
    }
    fn with_priority(content: String, sender: String, priority: i32) -> Self {
        return Message { content: content, sender: sender, priority: priority };
    }
}

fn main() {
    let msg1 = Message { content: String::from("Hello World"), sender: String::from("Alice"), priority: 1 };
    println!("{}", msg1.content);
    println!("{}", msg1.sender);
    let msg2 = Message::new(String::from("Test message"), String::from("Bob"));
    println!("{}", msg2.content);
    println!("{}", msg2.sender);
    let msg3 = Message::with_priority(String::from("Urgent"), String::from("Admin"), (10) as i32);
    println!("{}", msg3.content);
    println!("{}", msg3.priority);
    let greeting = Greeting::new(String::from("Welcome!"));
    println!("{}", greeting.text);
}