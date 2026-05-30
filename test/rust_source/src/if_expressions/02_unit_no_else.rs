fn main() {
    let debug = true;
    let result = if debug {
        println!("debug")
    } else {
        ()
    };
    println!("done");
}