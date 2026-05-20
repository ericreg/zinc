fn main() {
    let pairs = vec![(1, 2), (3, 4)];
    let mut total = 0;
    for (a, b) in pairs.iter().cloned() {
        println!("{}", a);
        println!("{}", b);
        total = (total + a);
        total = (total + b);
    }
    println!("{}", total);
    let triplets = vec![(1, 2, 3)];
    let mut triplet_total = 0;
    for (a, b, c) in triplets.iter().cloned() {
        triplet_total = (triplet_total + a);
        triplet_total = (triplet_total + b);
        triplet_total = (triplet_total + c);
    }
    println!("{}", triplet_total);
}