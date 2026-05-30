struct strings_01_raw_multiline__Message {
    pub body: String,
}

impl Default for strings_01_raw_multiline__Message {
    fn default() -> Self {
        Self { body: String::new() }
    }
}

fn strings_01_raw_multiline__echo_String(text: String) {
    println!("{}", text);
}

fn main() {
    let poem = r"roses are red
    violets are blue";
    let tick = r"literal backtick: `";
    let braces = r"{not interpolation}";
    let path = r"c:\temp\logs";
    strings_01_raw_multiline__echo_String(String::from(r"from helper
    second line"));
    let msg = strings_01_raw_multiline__Message { body: String::from(r#"struct field
    with "quotes" and \slashes\"#) };
    println!("{}", poem);
    println!("{}", tick);
    println!("{}", braces);
    println!("{}", path);
    println!("{}", msg.body);
}