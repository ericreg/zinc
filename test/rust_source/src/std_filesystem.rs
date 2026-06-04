fn __zinc_fs_exists(path: String) -> bool {
    std::fs::metadata(path).is_ok()
}

fn __zinc_fs_mkdir(path: String) -> Result<(), String> {
    std::fs::create_dir_all(path).map_err(|error| error.to_string())
}

fn __zinc_fs_read_text(path: String) -> Result<String, String> {
    std::fs::read_to_string(path).map_err(|error| error.to_string())
}

fn __zinc_fs_write_text(path: String, contents: String) -> Result<(), String> {
    std::fs::write(path, contents).map_err(|error| error.to_string())
}

fn __zinc_fs_read_lines(path: String) -> Result<Vec<String>, String> {
    std::fs::read_to_string(path).map(|contents| {
        contents.lines().map(|line| line.to_string()).collect()
    }).map_err(|error| error.to_string())
}

fn __zinc_fs_write_lines(path: String, lines: &Vec<String>) -> Result<(), String> {
    std::fs::write(path, lines.join("\n")).map_err(|error| error.to_string())
}

fn std_filesystem__exists_String(path: String) -> bool {
    return __zinc_fs_exists(path);
}

fn std_filesystem__mkdir_String(path: String) -> Result<(), String> {
    return __zinc_fs_mkdir(path);
}

fn std_filesystem__read_lines_String(path: String) -> Result<Vec<String>, String> {
    return __zinc_fs_read_lines(path);
}

fn std_filesystem__read_text_String(path: String) -> Result<String, String> {
    return __zinc_fs_read_text(path);
}

fn std_filesystem__write_text_String_String(path: String, contents: String) -> Result<(), String> {
    return __zinc_fs_write_text(path, contents);
}

fn main() {
    std_filesystem__mkdir_String(String::from("zinc_fs_tmp"));
    println!("{}", std_filesystem__exists_String(String::from("zinc_fs_tmp")));
    std_filesystem__write_text_String_String(String::from("zinc_fs_tmp/notes.txt"), String::from("hello zinc"));
    let text_result = std_filesystem__read_text_String(String::from("zinc_fs_tmp/notes.txt"));
    {
        let __zinc_match_42_69 = text_result;
        match __zinc_match_42_69.clone() {
            Ok(contents) => {
                println!("{}", contents);
            },
            Err(error) => {
                println!("read_text error");
            },
        }
    }
    std_filesystem__write_text_String_String(String::from("zinc_fs_tmp/lines.txt"), String::from("alpha\nbeta"));
    let lines_result = std_filesystem__read_lines_String(String::from("zinc_fs_tmp/lines.txt"));
    {
        let __zinc_match_86_123 = lines_result;
        match __zinc_match_86_123.clone() {
            Ok(lines) => {
                println!("{}", lines[0]);
                println!("{}", lines[1]);
            },
            Err(error) => {
                println!("read_lines error");
            },
        }
    }
}