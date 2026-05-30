#[derive(Clone)]
enum enums_02_payload_match__Message {
    Quit,
    Move { x: i32, y: i32 },
    Write { text: String },
}

fn enums_02_payload_match__handle_Enum_enums_02_payload_match__Message(msg: enums_02_payload_match__Message) {
    {
        let __zinc_match_29_73 = msg;
        match __zinc_match_29_73.clone() {
            enums_02_payload_match__Message::Quit => {
                println!("quit");
            },
            enums_02_payload_match__Message::Move { x, y } => {
                println!("move {} {}", x, y);
            },
            enums_02_payload_match__Message::Write { text } => {
                println!("{}", text);
            },
        }
    }
}

fn main() {
    let first = enums_02_payload_match__Message::Move { x: 10, y: 20 };
    let second = enums_02_payload_match__Message::Write { text: String::from("hello") };
    let items = vec![first, second, enums_02_payload_match__Message::Quit];
    enums_02_payload_match__handle_Enum_enums_02_payload_match__Message(items[0].clone());
    enums_02_payload_match__handle_Enum_enums_02_payload_match__Message(items[1].clone());
    enums_02_payload_match__handle_Enum_enums_02_payload_match__Message(items[2].clone());
}