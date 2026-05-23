struct structs_09_composition_orthogonal__File {
    pub path: String,
}

impl structs_09_composition_orthogonal__File {
    fn file_label(&self) -> String {
        return format!("file:{}", self.path);
    }
}

struct structs_09_composition_orthogonal__Item {
    pub path: String,
    pub text: String,
    pub timestamp: i64,
    pub owner_id: i32,
}

impl structs_09_composition_orthogonal__Item {
    fn file_label(&self) -> String {
        return format!("file:{}", self.path);
    }
    fn summary(&self) -> String {
        return format!("{}@{}", self.text, self.timestamp);
    }
    fn owner(&self) -> i32 {
        return self.owner_id;
    }
}

struct structs_09_composition_orthogonal__Message {
    pub text: String,
    pub timestamp: i64,
}

impl structs_09_composition_orthogonal__Message {
    fn summary(&self) -> String {
        return format!("{}@{}", self.text, self.timestamp);
    }
}

fn main() {
    let item = structs_09_composition_orthogonal__Item { path: String::from("/tmp/zinc.txt"), text: String::from("hello"), timestamp: 7, owner_id: 42 };
    println!("{}", item.path);
    println!("{}", item.text);
    println!("{}", item.timestamp);
    println!("{}", item.owner());
    println!("{}", item.file_label());
    println!("{}", item.summary());
}