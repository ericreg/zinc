use zinc_internal::{Channel};

async fn concurrency_channels_06_param_receive_range__sum_Channel(values: Channel<i64>) -> i64 {
    let mut total = 0;
    {
        let __zinc_channel_iter_1 = values.clone();
        loop {
            let Some(value) = __zinc_channel_iter_1.recv_option().await else {
                break;
            };
            total = (total + value);
        }
    }
    return total;
}

#[tokio::main]
async fn main() {
    let values = Channel::<i64>::unbounded();
    values.send(1).await;
    values.send(2).await;
    values.send(3).await;
    values.close();
    println!("{}", concurrency_channels_06_param_receive_range__sum_Channel(values.clone()).await);
}