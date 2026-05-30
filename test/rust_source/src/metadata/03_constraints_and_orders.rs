use zinc_internal::{FunctionParameterMeta, StructMeta, TypeMeta};

#[derive(Clone, Default)]
struct __ZincAnonStruct_AnonStruct_a_i64_b_String_c_bool {
    a: i64,
    b: String,
    c: bool,
}

struct metadata_03_constraints_and_orders__Circle {
    pub name: String,
    pub radius: i64,
}

impl Default for metadata_03_constraints_and_orders__Circle {
    fn default() -> Self {
        Self { name: String::new(), radius: 0 }
    }
}

impl metadata_03_constraints_and_orders__Circle {
    fn area(&self) -> i64 {
        return (self.radius * self.radius);
    }
}

struct metadata_03_constraints_and_orders__Rectangle {
    pub name: String,
    pub width: i64,
}

impl Default for metadata_03_constraints_and_orders__Rectangle {
    fn default() -> Self {
        Self { name: String::new(), width: 0 }
    }
}

impl metadata_03_constraints_and_orders__Rectangle {
    fn area(&self) -> i64 {
        return self.width;
    }
}

struct metadata_03_constraints_and_orders__Shape {
    pub name: String,
}

impl Default for metadata_03_constraints_and_orders__Shape {
    fn default() -> Self {
        Self { name: String::new() }
    }
}

struct metadata_03_constraints_and_orders__Shape2D {
    pub name: String,
}

impl Default for metadata_03_constraints_and_orders__Shape2D {
    fn default() -> Self {
        Self { name: String::new() }
    }
}

impl metadata_03_constraints_and_orders__Shape2D {
    fn area() -> i64 {
        return 0;
    }
}

struct metadata_03_constraints_and_orders__Square {
    pub name: String,
    pub side: i64,
}

impl Default for metadata_03_constraints_and_orders__Square {
    fn default() -> Self {
        Self { name: String::new(), side: 0 }
    }
}

impl metadata_03_constraints_and_orders__Square {
    fn area(&self) -> i64 {
        return (self.side * self.side);
    }
}

// infer-backed struct family metadata_03_constraints_and_orders__Triple uses synthesized concrete shapes

fn metadata_03_constraints_and_orders__accept_nominal_Struct_metadata_03_constraints_and_orders_Circle(shape: metadata_03_constraints_and_orders__Circle) {
    println!("{:?}", FunctionParameterMeta { kind: String::from("parameter"), name: String::from("shape"), fqn: String::from("metadata/03_constraints_and_orders/accept_nominal/shape"), module_fqn: String::from("metadata/03_constraints_and_orders"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/03_constraints_and_orders.zn"), line_num: 48, is_public: false, index: 0, value_type: TypeMeta { kind: String::from("struct"), name: String::from("Circle"), fqn: String::from("metadata/03_constraints_and_orders/Circle"), family_name: String::from("Circle"), family_fqn: String::from("metadata/03_constraints_and_orders/Circle"), args: Vec::<TypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, declared_type: TypeMeta { kind: String::from("unknown"), name: String::from("unknown"), fqn: String::from("unknown"), family_name: String::from("unknown"), family_fqn: String::from("unknown"), args: Vec::<TypeMeta>::new(), is_named: false, is_bounded: false, infer_slots: Vec::<String>::new() }, has_declared_type: false, has_default: false });
    println!("{:?}", TypeMeta { kind: String::from("struct"), name: String::from("Circle"), fqn: String::from("metadata/03_constraints_and_orders/Circle"), family_name: String::from("Circle"), family_fqn: String::from("metadata/03_constraints_and_orders/Circle"), args: Vec::<TypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() });
    println!("{}", shape.area());
}

fn metadata_03_constraints_and_orders__accept_nominal_Struct_metadata_03_constraints_and_orders_Square(shape: metadata_03_constraints_and_orders__Square) {
    println!("{:?}", FunctionParameterMeta { kind: String::from("parameter"), name: String::from("shape"), fqn: String::from("metadata/03_constraints_and_orders/accept_nominal/shape"), module_fqn: String::from("metadata/03_constraints_and_orders"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/03_constraints_and_orders.zn"), line_num: 48, is_public: false, index: 0, value_type: TypeMeta { kind: String::from("struct"), name: String::from("Square"), fqn: String::from("metadata/03_constraints_and_orders/Square"), family_name: String::from("Square"), family_fqn: String::from("metadata/03_constraints_and_orders/Square"), args: Vec::<TypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, declared_type: TypeMeta { kind: String::from("unknown"), name: String::from("unknown"), fqn: String::from("unknown"), family_name: String::from("unknown"), family_fqn: String::from("unknown"), args: Vec::<TypeMeta>::new(), is_named: false, is_bounded: false, infer_slots: Vec::<String>::new() }, has_declared_type: false, has_default: false });
    println!("{:?}", TypeMeta { kind: String::from("struct"), name: String::from("Square"), fqn: String::from("metadata/03_constraints_and_orders/Square"), family_name: String::from("Square"), family_fqn: String::from("metadata/03_constraints_and_orders/Square"), args: Vec::<TypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() });
    println!("{}", shape.area());
}

fn metadata_03_constraints_and_orders__accept_structural_Struct_metadata_03_constraints_and_orders_Rectangle(shape: metadata_03_constraints_and_orders__Rectangle) {
    println!("{:?}", FunctionParameterMeta { kind: String::from("parameter"), name: String::from("shape"), fqn: String::from("metadata/03_constraints_and_orders/accept_structural/shape"), module_fqn: String::from("metadata/03_constraints_and_orders"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/03_constraints_and_orders.zn"), line_num: 55, is_public: false, index: 0, value_type: TypeMeta { kind: String::from("struct"), name: String::from("Rectangle"), fqn: String::from("metadata/03_constraints_and_orders/Rectangle"), family_name: String::from("Rectangle"), family_fqn: String::from("metadata/03_constraints_and_orders/Rectangle"), args: Vec::<TypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, declared_type: TypeMeta { kind: String::from("unknown"), name: String::from("unknown"), fqn: String::from("unknown"), family_name: String::from("unknown"), family_fqn: String::from("unknown"), args: Vec::<TypeMeta>::new(), is_named: false, is_bounded: false, infer_slots: Vec::<String>::new() }, has_declared_type: false, has_default: false });
    println!("{:?}", TypeMeta { kind: String::from("struct"), name: String::from("Rectangle"), fqn: String::from("metadata/03_constraints_and_orders/Rectangle"), family_name: String::from("Rectangle"), family_fqn: String::from("metadata/03_constraints_and_orders/Rectangle"), args: Vec::<TypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() });
    println!("{}", shape.area());
}

fn main() {
    let triple = __ZincAnonStruct_AnonStruct_a_i64_b_String_c_bool { a: 9, b: String::from("ok"), c: true };
    let circle = metadata_03_constraints_and_orders__Circle { name: String::from("circle"), radius: 4 };
    let square = metadata_03_constraints_and_orders__Square { name: String::from("square"), side: 3 };
    let rect = metadata_03_constraints_and_orders__Rectangle { name: String::from("rect"), width: 5 };
    println!("{}", 67);
    println!("{:?}", StructMeta { kind: String::from("struct"), name: String::from("Triple"), fqn: String::from("metadata/03_constraints_and_orders/Triple"), module_fqn: String::from("metadata/03_constraints_and_orders"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/03_constraints_and_orders.zn"), line_num: 36, is_public: true, type_info: TypeMeta { kind: String::from("struct"), name: String::from("Triple"), fqn: String::from("metadata/03_constraints_and_orders/Triple"), family_name: String::from("Triple"), family_fqn: String::from("metadata/03_constraints_and_orders/Triple"), args: Vec::<TypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: vec![String::from("a"), String::from("b"), String::from("c")] } });
    println!("{:?}", TypeMeta { kind: String::from("struct"), name: String::from("Triple<i64, String, bool>"), fqn: String::from("metadata/03_constraints_and_orders/Triple<i64, String, bool>"), family_name: String::from("Triple"), family_fqn: String::from("metadata/03_constraints_and_orders/Triple"), args: vec![TypeMeta { kind: String::from("primitive"), name: String::from("i64"), fqn: String::from("i64"), family_name: String::from("i64"), family_fqn: String::from("i64"), args: Vec::<TypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, TypeMeta { kind: String::from("primitive"), name: String::from("String"), fqn: String::from("String"), family_name: String::from("String"), family_fqn: String::from("String"), args: Vec::<TypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, TypeMeta { kind: String::from("primitive"), name: String::from("bool"), fqn: String::from("bool"), family_name: String::from("bool"), family_fqn: String::from("bool"), args: Vec::<TypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }], is_named: true, is_bounded: false, infer_slots: vec![String::from("a"), String::from("b"), String::from("c")] });
    println!("{}", true);
    println!("{}", false);
    println!("{}", true);
    println!("{}", true);
    println!("{}", false);
    metadata_03_constraints_and_orders__accept_nominal_Struct_metadata_03_constraints_and_orders_Circle(circle);
    metadata_03_constraints_and_orders__accept_nominal_Struct_metadata_03_constraints_and_orders_Square(square);
    metadata_03_constraints_and_orders__accept_structural_Struct_metadata_03_constraints_and_orders_Rectangle(rect);
    println!("{:?}", vec![TypeMeta { kind: String::from("struct"), name: String::from("Shape2D"), fqn: String::from("metadata/03_constraints_and_orders/Shape2D"), family_name: String::from("Shape2D"), family_fqn: String::from("metadata/03_constraints_and_orders/Shape2D"), args: Vec::<TypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, TypeMeta { kind: String::from("struct"), name: String::from("Shape"), fqn: String::from("metadata/03_constraints_and_orders/Shape"), family_name: String::from("Shape"), family_fqn: String::from("metadata/03_constraints_and_orders/Shape"), args: Vec::<TypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }]);
    println!("{:?}", vec![TypeMeta { kind: String::from("struct"), name: String::from("Shape"), fqn: String::from("metadata/03_constraints_and_orders/Shape"), family_name: String::from("Shape"), family_fqn: String::from("metadata/03_constraints_and_orders/Shape"), args: Vec::<TypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, TypeMeta { kind: String::from("struct"), name: String::from("Shape2D"), fqn: String::from("metadata/03_constraints_and_orders/Shape2D"), family_name: String::from("Shape2D"), family_fqn: String::from("metadata/03_constraints_and_orders/Shape2D"), args: Vec::<TypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }]);
}