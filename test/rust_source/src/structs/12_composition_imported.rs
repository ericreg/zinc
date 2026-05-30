struct structs_12_composition_imported__Post {
    pub created_by: String,
    pub body: String,
    pub id: i32,
}

impl Default for structs_12_composition_imported__Post {
    fn default() -> Self {
        Self { created_by: String::new(), body: String::new(), id: 0 }
    }
}

impl structs_12_composition_imported__Post {
    fn creator(&self) -> String {
        return format!("{}", self.created_by);
    }
}

struct structs__composition_parts__Audit {
    pub created_by: String,
}

impl Default for structs__composition_parts__Audit {
    fn default() -> Self {
        Self { created_by: String::new() }
    }
}

impl structs__composition_parts__Audit {
    fn creator(&self) -> String {
        return format!("{}", self.created_by);
    }
}

struct structs__composition_parts__Content {
    pub body: String,
}

impl Default for structs__composition_parts__Content {
    fn default() -> Self {
        Self { body: String::new() }
    }
}

fn main() {
    let post = structs_12_composition_imported__Post { created_by: String::from("alice"), body: String::from("hello world"), id: 3 };
    println!("{}", post.id);
    println!("{}", post.created_by);
    println!("{}", post.body);
    println!("{}", post.creator());
}