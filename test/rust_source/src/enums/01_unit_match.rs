#[derive(Clone)]
enum enums_01_unit_match__Status {
    Idle,
    Working,
    Done,
}

fn enums_01_unit_match__describe_Enum_enums_01_unit_match__Status(status: enums_01_unit_match__Status) {
    {
        let __zinc_match_15_51 = status;
        match __zinc_match_15_51.clone() {
            enums_01_unit_match__Status::Idle => {
                println!("idle");
            },
            enums_01_unit_match__Status::Working => {
                println!("working");
            },
            enums_01_unit_match__Status::Done => {
                println!("done");
            },
        }
    }
}

fn main() {
    let current = enums_01_unit_match__Status::Working;
    let history = vec![enums_01_unit_match__Status::Idle, current, enums_01_unit_match__Status::Done];
    enums_01_unit_match__describe_Enum_enums_01_unit_match__Status(history[0].clone());
    enums_01_unit_match__describe_Enum_enums_01_unit_match__Status(history[1].clone());
    enums_01_unit_match__describe_Enum_enums_01_unit_match__Status(history[2].clone());
}