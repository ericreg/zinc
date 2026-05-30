static MODULES__LIB_IO__TAG: std::sync::LazyLock<String> = std::sync::LazyLock::new(|| String::from("disk"));

struct modules__lib_io__File {
    pub name: String,
}

impl Default for modules__lib_io__File {
    fn default() -> Self {
        Self { name: String::new() }
    }
}

fn modules__lib_io__size() -> i64 {
    return 7;
}

fn main() {
    let file = modules__lib_io__File { name: String::from("notes") };
    println!("{}", file.name);
    println!("{}", modules__lib_io__size());
    println!("{}", (*MODULES__LIB_IO__TAG).clone());
}