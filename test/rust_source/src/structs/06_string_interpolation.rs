struct structs_06_string_interpolation__Person {
    pub name: String,
    pub age: i32,
}

impl structs_06_string_interpolation__Person {
    fn greeting(&self) -> String {
        return format!("Hello, my name is {}", self.name);
    }
    fn describe(&self) -> String {
        return format!("Person: {}, Age: {}", self.name, self.age);
    }
    fn new(name: String, age: i32) -> Self {
        return structs_06_string_interpolation__Person { name: name, age: age };
    }
}

struct structs_06_string_interpolation__Rectangle {
    pub width: i32,
    pub height: i32,
}

impl structs_06_string_interpolation__Rectangle {
    fn area(&self) -> i32 {
        return (self.width * self.height);
    }
    fn describe(&self) -> String {
        return format!("Rectangle {}x{}", self.width, self.height);
    }
}

fn main() {
    let person = structs_06_string_interpolation__Person::new(String::from("Alice"), (30) as i32);
    println!("{}", person.greeting());
    println!("{}", person.describe());
    let rect = structs_06_string_interpolation__Rectangle { width: 10, height: 5 };
    println!("{}", rect.describe());
    println!("{}", rect.area());
}