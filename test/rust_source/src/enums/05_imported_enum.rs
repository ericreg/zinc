#[derive(Clone)]
enum enums__lib_messages__Remote {
    Ready,
    Payload { text: String },
}

fn enums_05_imported_enum__print_remote_Enum_enums__lib_messages__Remote(item: enums__lib_messages__Remote) {
    {
        let __zinc_match_18_50 = item;
        match __zinc_match_18_50.clone() {
            enums__lib_messages__Remote::Ready => {
                println!("ready");
            },
            enums__lib_messages__Remote::Payload { text } => {
                println!("{}", text);
            },
        }
    }
}

fn enums__lib_messages__ready() -> enums__lib_messages__Remote {
    return enums__lib_messages__Remote::Ready;
}

fn main() {
    let first = enums__lib_messages__ready();
    let second = enums__lib_messages__Remote::Payload { text: String::from("remote") };
    enums_05_imported_enum__print_remote_Enum_enums__lib_messages__Remote(first);
    enums_05_imported_enum__print_remote_Enum_enums__lib_messages__Remote(second);
}