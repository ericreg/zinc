struct structs_10_composition_merge_fields__File {
    pub id: i32,
    pub path: String,
}

impl Default for structs_10_composition_merge_fields__File {
    fn default() -> Self {
        Self { id: 0, path: String::new() }
    }
}

impl structs_10_composition_merge_fields__File {
    fn source() -> i64 {
        return 1;
    }
}

struct structs_10_composition_merge_fields__Item {
    pub id: i64,
    pub path: String,
    pub text: String,
}

impl Default for structs_10_composition_merge_fields__Item {
    fn default() -> Self {
        Self { id: 99, path: String::new(), text: String::new() }
    }
}

impl structs_10_composition_merge_fields__Item {
    fn source() -> i64 {
        return 2;
    }
    fn label(&self) -> String {
        return format!("local {}", self.id);
    }
    fn describe(&self) -> String {
        return format!("{}:{}:{}", self.id, self.path, self.text);
    }
}

struct structs_10_composition_merge_fields__Message {
    pub id: i64,
    pub text: String,
}

impl Default for structs_10_composition_merge_fields__Message {
    fn default() -> Self {
        Self { id: 0, text: String::new() }
    }
}

impl structs_10_composition_merge_fields__Message {
    fn source() -> i64 {
        return 2;
    }
}

fn main() {
    let item = structs_10_composition_merge_fields__Item { id: 99, path: String::from("/tmp/data"), text: String::from("payload") };
    println!("{}", item.id);
    println!("{}", item.path);
    println!("{}", item.text);
    println!("{}", structs_10_composition_merge_fields__Item::source());
    println!("{}", item.label());
    println!("{}", item.describe());
}