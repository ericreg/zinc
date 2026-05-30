use zinc_internal::{__ZincChannel};

#[derive(Clone, Default)]
struct __ZincAnonStruct_AnonStruct_id_i64_name_String {
    id: i64,
    name: String,
}

#[derive(Clone, Default)]
struct __ZincAnonStruct_AnonStruct_ready_bool {
    ready: bool,
}

#[tokio::main]
async fn main() {
    let items = vec![__ZincAnonStruct_AnonStruct_id_i64_name_String { id: 1, name: String::from("one") }, __ZincAnonStruct_AnonStruct_id_i64_name_String { id: 2, name: String::from("two") }];
    let pair = (__ZincAnonStruct_AnonStruct_id_i64_name_String { id: 3, name: String::from("three") }, __ZincAnonStruct_AnonStruct_ready_bool { ready: true });
    let (first, status) = pair;
    let jobs = __ZincChannel::<__ZincAnonStruct_AnonStruct_id_i64_name_String>::unbounded();
    jobs.send(__ZincAnonStruct_AnonStruct_id_i64_name_String { id: 4, name: String::from("four") }).await;
    let received = jobs.recv().await;
    println!("{}", items[0].id);
    println!("{}", items[1].name);
    println!("{}", first.name);
    println!("{}", status.ready);
    println!("{}", received.id);
    println!("{}", received.name);
}