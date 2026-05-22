struct structs_02_private_fields__User {
    _id: i32,
    _password: String,
    pub username: String,
    pub email: String,
}

fn main() {
    let user = structs_02_private_fields__User { _id: 42, _password: String::from("secret123"), username: String::from("alice"), email: String::from("alice@example.com") };
    println!("{}", user.username);
    println!("{}", user.email);
    println!("{}", user._id);
}