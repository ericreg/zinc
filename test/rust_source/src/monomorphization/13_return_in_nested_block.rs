fn find_value_Vec_i64_i64(arr: &Vec<i64>, target: i64) -> i64 {
    let mut i = 0;
    while (i < (arr.len() as i64)) {
        if (arr[(i as usize)] == target) {
            return i;
        }
        i = (i + 1);
    }
    return (-1);
}

fn sum_until_Vec_i64_i64(arr: &Vec<i64>, limit: i64) -> i64 {
    let mut total = 0;
    let mut i = 0;
    while (i < (arr.len() as i64)) {
        if ((total + arr[(i as usize)]) > limit) {
            return total;
        }
        total = (total + arr[(i as usize)]);
        i = (i + 1);
    }
    return total;
}

fn main() {
    let nums = vec![10, 20, 30, 40, 50];
    let idx1 = find_value_Vec_i64_i64(&nums, 30);
    println!("find 30: {}", idx1);
    let idx2 = find_value_Vec_i64_i64(&nums, 99);
    println!("find 99: {}", idx2);
    let sum1 = sum_until_Vec_i64_i64(&nums, 50);
    println!("sum until 50: {}", sum1);
    let sum2 = sum_until_Vec_i64_i64(&nums, 1000);
    println!("sum until 1000: {}", sum2);
}