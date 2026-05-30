use std::sync::{Arc, Mutex};

#[derive(Clone)]
struct __ZincClosureEnv_closures_13_captured_struct_field_mutation___lambda_closures_13_captured_struct_field_mutation__main_19_32 {
    counter: Arc<Mutex<closures_13_captured_struct_field_mutation__Counter>>,
}

#[derive(Clone)]
enum __ZincCallable_Unit_to_Unit {
    Closed,
    V0(__ZincClosureEnv_closures_13_captured_struct_field_mutation___lambda_closures_13_captured_struct_field_mutation__main_19_32),
}

impl Default for __ZincCallable_Unit_to_Unit {
    fn default() -> Self {
        Self::Closed
    }
}

impl __ZincCallable_Unit_to_Unit {
    fn call(&self, ) {
        match self {
            Self::Closed => panic!("callable used after closed receive"),
            Self::V0(env) => { closures_13_captured_struct_field_mutation____lambda_closures_13_captured_struct_field_mutation__main_19_32(env.clone()); }
        }
    }
}

struct closures_13_captured_struct_field_mutation__Counter {
    pub count: i64,
}

impl Default for closures_13_captured_struct_field_mutation__Counter {
    fn default() -> Self {
        Self { count: 0 }
    }
}

fn closures_13_captured_struct_field_mutation____lambda_closures_13_captured_struct_field_mutation__main_19_32(__env: __ZincClosureEnv_closures_13_captured_struct_field_mutation___lambda_closures_13_captured_struct_field_mutation__main_19_32) {
    let __zv_closures_13_captured_struct_field_mutation____lambda_closures_13_captured_struct_field_mutation__main_19_32_counter_Struct = __env.counter.clone();
    let __zinc_captured_field_23_31 = (__zv_closures_13_captured_struct_field_mutation____lambda_closures_13_captured_struct_field_mutation__main_19_32_counter_Struct.lock().unwrap().count + 1);
    __zv_closures_13_captured_struct_field_mutation____lambda_closures_13_captured_struct_field_mutation__main_19_32_counter_Struct.lock().unwrap().count = __zinc_captured_field_23_31;
}

fn main() {
    let __zv_closures_13_captured_struct_field_mutation__main_counter_Struct = Arc::new(Mutex::new(closures_13_captured_struct_field_mutation__Counter { count: 0 }));
    let bump = __ZincCallable_Unit_to_Unit::V0(__ZincClosureEnv_closures_13_captured_struct_field_mutation___lambda_closures_13_captured_struct_field_mutation__main_19_32 { counter: __zv_closures_13_captured_struct_field_mutation__main_counter_Struct.clone() });
    bump.call();
    bump.call();
    println!("{}", __zv_closures_13_captured_struct_field_mutation__main_counter_Struct.lock().unwrap().count);
}