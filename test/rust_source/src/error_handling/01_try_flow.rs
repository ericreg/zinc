fn error_handling_01_try_flow__guarded_bool(flag: bool) -> Result<i64, String> {
    return (|| -> Result<i64, String> {
        if (!flag) {
            return Err(String::from("nope"));
        }
        Ok(9)
    })();
}

fn error_handling_01_try_flow__maybe_bool(flag: bool) -> Option<i64> {
    if flag {
        return Some(7);
    }
    return None;
}

fn error_handling_01_try_flow__parse_bool(flag: bool) -> Result<i64, String> {
    if flag {
        return Ok(41);
    }
    return Err(String::from("boom"));
}

fn error_handling_01_try_flow__plus_two_bool(flag: bool) -> Result<i64, String> {
    return (|| -> Result<i64, String> {
        let value = (error_handling_01_try_flow__parse_bool(flag))?;
        Ok((value + 1))
    })();
}

fn main() {
    let block_value = {
        let left = 1;
        let right = 2;
        (left + right)
    };
    println!("{}", block_value);
    let result = (|| -> Result<i64, String> {
        let mut value = (error_handling_01_try_flow__plus_two_bool(true))?;
        Ok((value + 1))
    })();
    {
        let __zinc_match_148_175 = result;
        match __zinc_match_148_175.clone() {
            Ok(value) => {
                println!("{}", value);
            },
            Err(message) => {
                println!("{}", message);
            },
        }
    }
    {
        let __zinc_match_176_211 = (|| -> Option<i64> {
        let value = (error_handling_01_try_flow__maybe_bool(false))?;
        Some((value + 1))
    })();
        match __zinc_match_176_211.clone() {
            Some(value) => {
                println!("{}", value);
            },
            None => {
                println!("none");
            },
        }
    }
    {
        let __zinc_match_212_242 = error_handling_01_try_flow__guarded_bool(false);
        match __zinc_match_212_242.clone() {
            Ok(value) => {
                println!("{}", value);
            },
            Err(message) => {
                println!("{}", message);
            },
        }
    }
    let typed_result: Result<i64, String> = Ok(1);
    let typed_option: Option<String> = Some(String::from("hi"));
    println!("{}", String::from("Result"));
    println!("{}", String::from("i64"));
    println!("{}", String::from("String"));
    println!("{}", String::from("Option"));
    println!("{}", String::from("String"));
}