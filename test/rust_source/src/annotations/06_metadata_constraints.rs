#[derive(Clone, Default)]
struct __ZincAnonStruct_AnonStruct_a_bool_b_String {
    a: bool,
    b: String,
}

#[derive(Clone)]
enum annotations_06_metadata_constraints__Color {
    Red,
    Blue,
}

struct annotations_06_metadata_constraints__Audit {
    pub created_at: i64,
}

impl Default for annotations_06_metadata_constraints__Audit {
    fn default() -> Self {
        Self { created_at: 0 }
    }
}

struct annotations_06_metadata_constraints__Circle {
    pub name: String,
    pub radius: f64,
}

impl Default for annotations_06_metadata_constraints__Circle {
    fn default() -> Self {
        Self { name: String::new(), radius: 0.0 }
    }
}

impl annotations_06_metadata_constraints__Circle {
    fn area(&self) -> f64 {
        return (self.radius * self.radius);
    }
}

struct annotations_06_metadata_constraints__Named {
    pub name: String,
}

impl Default for annotations_06_metadata_constraints__Named {
    fn default() -> Self {
        Self { name: String::new() }
    }
}

// infer-backed struct family annotations_06_metadata_constraints__Pair uses synthesized concrete shapes

struct annotations_06_metadata_constraints__Rectangle {
    pub name: String,
    pub width: i64,
}

impl Default for annotations_06_metadata_constraints__Rectangle {
    fn default() -> Self {
        Self { name: String::new(), width: 0 }
    }
}

impl annotations_06_metadata_constraints__Rectangle {
    fn area(&self) -> i64 {
        return self.width;
    }
}

struct annotations_06_metadata_constraints__Shape2D {
    pub name: String,
}

impl Default for annotations_06_metadata_constraints__Shape2D {
    fn default() -> Self {
        Self { name: String::new() }
    }
}

impl annotations_06_metadata_constraints__Shape2D {
    fn area() -> i64 {
        return 0;
    }
}

struct annotations_06_metadata_constraints__TaggedCircle {
    pub created_at: i64,
    pub name: String,
    pub radius: f64,
    pub tag: String,
}

impl Default for annotations_06_metadata_constraints__TaggedCircle {
    fn default() -> Self {
        Self { created_at: 0, name: String::new(), radius: 0.0, tag: String::new() }
    }
}

impl annotations_06_metadata_constraints__TaggedCircle {
    fn area(&self) -> f64 {
        return (self.radius * self.radius);
    }
}

fn annotations_06_metadata_constraints__print_shape_Struct_annotations_06_metadata_constraints_Rectangle(shape: annotations_06_metadata_constraints__Rectangle) {
    println!("{}", String::from("print_shape"));
    println!("{}", shape.name);
    println!("{}", shape.area());
}

fn main() {
    println!("{}", 58);
    let pair = __ZincAnonStruct_AnonStruct_a_bool_b_String { a: true, b: String::from("ok") };
    let item = annotations_06_metadata_constraints__TaggedCircle { created_at: 7, name: String::from("circle"), radius: 3.0, tag: String::from("featured") };
    println!("{}", String::from("enum"));
    println!("{}", 1);
    println!("{}", String::from("Color"));
    println!("{}", String::from("builtin"));
    println!("{}", String::from("Pair"));
    println!("{}", String::from("bool"));
    println!("{}", String::from("String"));
    println!("{}", String::from("b"));
    println!("{}", String::from("Red"));
    println!("{}", String::from("created_at"));
    println!("{}", false);
    println!("{}", String::from("annotations/06_metadata_constraints/Audit"));
    println!("{}", String::from("tag"));
    println!("{}", true);
    println!("{}", String::from("Circle"));
    println!("{}", String::from("Shape2D"));
    println!("{}", String::from("Named"));
    println!("{}", String::from("TaggedCircle"));
    println!("{}", String::from("TaggedCircle"));
    println!("{}", false);
    println!("{}", true);
    println!("{}", false);
    println!("{}", true);
    annotations_06_metadata_constraints__print_shape_Struct_annotations_06_metadata_constraints_Rectangle(annotations_06_metadata_constraints__Rectangle { name: String::from("box"), width: 9 });
}