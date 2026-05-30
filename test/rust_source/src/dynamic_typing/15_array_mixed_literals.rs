fn main() {
    let ints = vec![1, 2, 3, 4, 5];
    println!("ints[0]: {}", ints[0]);
    println!("ints[4]: {}", ints[4]);
    let floats = vec![1.0, 2.0, 3.0];
    println!("floats[0]: {}", floats[0]);
    println!("floats[2]: {}", floats[2]);
    let bools = vec![true, false, true];
    println!("bools[0]: {}", bools[0]);
    println!("bools[1]: {}", bools[1]);
    let strings = vec!["a", "b", "c"];
    println!("strings[0]: {}", strings[0]);
    let first_int = vec![1, 2, 3];
    println!("first_int: {}, {}, {}", first_int[0], first_int[1], first_int[2]);
    let first_float = vec![1.0, 2.0, 3.0];
    println!("first_float: {}, {}, {}", first_float[0], first_float[1], first_float[2]);
    let single_int = vec![42];
    println!("single_int[0]: {}", single_int[0]);
    let single_float = vec![3.14];
    println!("single_float[0]: {}", single_float[0]);
    println!("test complete");
}