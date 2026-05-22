fn monomorphization_19_generic_with_arrays__first_Vec_f64(arr: &Vec<f64>) -> f64 {
    return arr[0];
}

fn monomorphization_19_generic_with_arrays__first_Vec_i64(arr: &Vec<i64>) -> i64 {
    return arr[0];
}

fn monomorphization_19_generic_with_arrays__last_Vec_f64(arr: &Vec<f64>) -> f64 {
    return arr[(((arr.len() as i64) - 1) as usize)];
}

fn monomorphization_19_generic_with_arrays__last_Vec_i64(arr: &Vec<i64>) -> i64 {
    return arr[(((arr.len() as i64) - 1) as usize)];
}

fn monomorphization_19_generic_with_arrays__sum_array_Vec_f64(arr: &Vec<f64>) -> f64 {
    let mut total = arr[0];
    let mut i = 1;
    while (i < (arr.len() as i64)) {
        total = (total + arr[(i as usize)]);
        i = (i + 1);
    }
    return total;
}

fn monomorphization_19_generic_with_arrays__sum_array_Vec_i64(arr: &Vec<i64>) -> i64 {
    let mut total = arr[0];
    let mut i = 1;
    while (i < (arr.len() as i64)) {
        total = (total + arr[(i as usize)]);
        i = (i + 1);
    }
    return total;
}

fn main() {
    let ints = vec![1, 2, 3, 4, 5];
    let floats = vec![1.0, 2.0, 3.0];
    let a = monomorphization_19_generic_with_arrays__first_Vec_i64(&ints);
    println!("first(ints): {}", a);
    let b = monomorphization_19_generic_with_arrays__first_Vec_f64(&floats);
    println!("first(floats): {}", b);
    let c = monomorphization_19_generic_with_arrays__last_Vec_i64(&ints);
    println!("last(ints): {}", c);
    let d = monomorphization_19_generic_with_arrays__last_Vec_f64(&floats);
    println!("last(floats): {}", d);
    let e = monomorphization_19_generic_with_arrays__sum_array_Vec_i64(&ints);
    println!("sum_array(ints): {}", e);
    let f = monomorphization_19_generic_with_arrays__sum_array_Vec_f64(&floats);
    println!("sum_array(floats): {}", f);
}