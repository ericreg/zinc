fn error_handling_02_main_result__run_bool(flag: bool) -> Result<(), String> {
    if flag {
        return Err(String::from("boom"));
    }
    return Ok(());
}

fn __zinc_main() -> Result<(), String> {
    return (|| -> Result<(), String> {
        Ok((error_handling_02_main_result__run_bool(false))?)
    })();
}

fn main() {
    if let Err(err) = __zinc_main() {
        eprintln!("{}", err);
        std::process::exit(1);
    }
}