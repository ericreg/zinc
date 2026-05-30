#[derive(Clone)]
enum enums_03_static_methods__Message {
    Quit,
    Move { x: i32, y: i32 },
}

impl enums_03_static_methods__Message {
    fn origin() -> Self {
        return enums_03_static_methods__Message::Move { x: 0, y: 0 };
    }
    fn quit() -> Self {
        return enums_03_static_methods__Message::Quit;
    }
}

fn enums_03_static_methods__print_msg_Enum_enums_03_static_methods__Message(msg: enums_03_static_methods__Message) {
    {
        let __zinc_match_52_82 = msg;
        match __zinc_match_52_82.clone() {
            enums_03_static_methods__Message::Quit => {
                println!("quit");
            },
            enums_03_static_methods__Message::Move { x, y } => {
                println!("{},{}", x, y);
            },
        }
    }
}

fn main() {
    enums_03_static_methods__print_msg_Enum_enums_03_static_methods__Message(enums_03_static_methods__Message::origin());
    enums_03_static_methods__print_msg_Enum_enums_03_static_methods__Message(enums_03_static_methods__Message::quit());
}