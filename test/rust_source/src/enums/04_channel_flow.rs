use zinc_internal::{Channel};

#[derive(Clone)]
enum enums_04_channel_flow__Signal {
    Start,
    Stop,
}

#[tokio::main]
async fn main() {
    let updates = Channel::<enums_04_channel_flow__Signal>::unbounded();
    updates.send(enums_04_channel_flow__Signal::Start).await;
    updates.send(enums_04_channel_flow__Signal::Stop).await;
    let first = updates.recv().await;
    let second = updates.recv().await;
    {
        let __zinc_match_34_59 = first;
        match __zinc_match_34_59.clone() {
            enums_04_channel_flow__Signal::Start => {
                println!("start");
            },
            enums_04_channel_flow__Signal::Stop => {
                println!("stop");
            },
        }
    }
    {
        let __zinc_match_60_85 = second;
        match __zinc_match_60_85.clone() {
            enums_04_channel_flow__Signal::Start => {
                println!("start");
            },
            enums_04_channel_flow__Signal::Stop => {
                println!("stop");
            },
        }
    }
}