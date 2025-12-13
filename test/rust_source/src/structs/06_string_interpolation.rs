struct Person {
    pub name: String,
    pub age: i32,
}

impl Person {
    fn greeting(&self) -> String {
        return format!("Hello, my name is {}", self.name);
    }

    fn describe(&self) -> String {
        return format!("Person: {}, Age: {}", self.name, self.age);
    }

    fn new(name: String, age: i32) -> Self {
        return Person {
            name: name,
            age: age,
        };
    }

}
struct Rectangle {
    pub width: i32,
    pub height: i32,
}

impl Rectangle {
    fn area(&self) -> i32 {
        return self.width * self.height;
    }

    fn describe(&self) -> String {
        return format!("Rectangle {}x{}", self.width, self.height);
    }

}
fn main() {
    let person = Person::new(String::from("Alice"), 30);
    println!("person.greeting()");
    println!("person.describe()");
    let rect = Rectangle {
        width: 10,
        height: 5,
    };
    println!("rect.describe()");
    println!("rect.area()");
}
