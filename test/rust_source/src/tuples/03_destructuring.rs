#[derive(Clone, Default)]
struct __ZincAnonStruct_AnonStruct_id_i64 {
    id: i64,
}

fn main() {
    let (a, b) = (2, 3);
    println!("{}", a);
    println!("{}", b);
    let (name, score) = (String::from("ada"), 9);
    println!("{}", name);
    println!("{}", score);
    let __zinc_multi_assign_41_47 = 1;
    let x = __zinc_multi_assign_41_47.clone();
    let y = __zinc_multi_assign_41_47.clone();
    let mut z = __zinc_multi_assign_41_47;
    println!("{} {} {}", x, y, z);
    let x = "cat";
    let y = 3.14;
    z = 3;
    println!("{} {} {}", x, y, z);
    let __zinc_multi_assign_65_73 = 1;
    let fx: f32 = (__zinc_multi_assign_65_73.clone() as f32);
    let fy: f32 = (__zinc_multi_assign_65_73.clone() as f32);
    let fz: f32 = (__zinc_multi_assign_65_73 as f32);
    println!("{} {} {}", fx, fy, fz);
    let (value, label, item) = (3.14, String::from("cat"), __ZincAnonStruct_AnonStruct_id_i64 { id: 123456 });
    println!("{}", value);
    println!("{}", label);
    println!("{}", item.id);
    let (nested_left, nested_pair) = (1, (2, 3));
    let (nested_a, nested_b) = nested_pair;
    println!("{} {} {}", nested_left, nested_a, nested_b);
    let (single,) = (99,);
    println!("{}", single);
    let __zinc_destructure_143_153 = (1, 2);
    let typed_a: f32 = (__zinc_destructure_143_153.0 as f32);
    let typed_b: f32 = (__zinc_destructure_143_153.1 as f32);
    println!("{} {}", typed_a, typed_b);
    let __zinc_multi_assign_158_162 = "dog";
    let mut sx = __zinc_multi_assign_158_162.clone();
    let mut sy = __zinc_multi_assign_158_162;
    println!("{} {}", sx, sy);
    sx = "cat";
    sy = "bird";
    println!("{} {}", sx, sy);
    let __zinc_multi_assign_177_186 = __ZincAnonStruct_AnonStruct_id_i64 { id: 7 };
    let p1 = __zinc_multi_assign_177_186.clone();
    let p2 = __zinc_multi_assign_177_186;
    println!("{} {}", p1.id, p2.id);
    let mut rx: f32 = (0 as f32);
    let mut ry: f32 = (0 as f32);
    let __zinc_multi_assign_201_205 = 2;
    rx = (__zinc_multi_assign_201_205.clone() as f32);
    ry = (__zinc_multi_assign_201_205 as f32);
    println!("{} {}", rx, ry);
    let (mut first, mut second) = (10, 20);
    (first, second) = (second, first);
    println!("{} {}", first, second);
}