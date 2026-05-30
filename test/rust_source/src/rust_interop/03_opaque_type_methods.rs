use std::ffi::OsString;
use std::mem::drop;
use std::path::PathBuf;

fn main() {
    let path = PathBuf::from(String::from("notes.txt"));
    let name = path.into_os_string();
    drop(name);
    println!("ok");
}