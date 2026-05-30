use zinc_internal::{Channel, FieldMeta, MethodMeta, MethodParameterMeta, TypeMeta, VariantMeta};
use std::collections::{HashMap, HashSet};

#[derive(Clone, Default)]
struct __ZincAnonStruct_AnonStruct_x_i64_y_String {
    x: i64,
    y: String,
}

struct metadata_02_type_meta__Base {
    pub version: i64,
    pub name: String,
}

impl Default for metadata_02_type_meta__Base {
    fn default() -> Self {
        Self { version: 1, name: String::new() }
    }
}

struct metadata_02_type_meta__Detail {
    pub level: i64,
}

impl Default for metadata_02_type_meta__Detail {
    fn default() -> Self {
        Self { level: 0 }
    }
}

impl metadata_02_type_meta__Detail {
    fn scale(&self, multiplier: i64) -> i64 {
        return (self.level * multiplier);
    }
}

struct metadata_02_type_meta__Node {
    pub version: i64,
    pub name: String,
    pub level: i64,
    pub enabled: bool,
}

impl Default for metadata_02_type_meta__Node {
    fn default() -> Self {
        Self { version: 1, name: String::new(), level: 0, enabled: false }
    }
}

impl metadata_02_type_meta__Node {
    fn scale(&self, multiplier: i64) -> i64 {
        return (self.level * multiplier);
    }
}

// infer-backed struct family metadata_02_type_meta__Pair uses synthesized concrete shapes

#[tokio::main]
async fn main() {
    let pair = __ZincAnonStruct_AnonStruct_x_i64_y_String { x: 7, y: String::from("seven") };
    let node = metadata_02_type_meta__Node { version: 1, name: String::from("root"), level: 2, enabled: true };
    let arr = vec![1, 2, 3];
    let tup = (1, String::from("two"), true);
    let scores = HashMap::from([(String::from("a"), 1), (String::from("b"), 2)]);
    let values = HashSet::from([1, 2, 3]);
    let ch = Channel::<i64>::unbounded();
    ch.send(1).await;
    let got = ch.recv().await;
    let buffered = Channel::<String>::bounded(2);
    buffered.send(String::from("ready")).await;
    let buffered_value = buffered.recv().await;
    println!("{:?}", TypeMeta { kind: String::from("primitive"), name: String::from("i64"), fqn: String::from("i64"), family_name: String::from("i64"), family_fqn: String::from("i64"), args: Vec::<TypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() });
    println!("{:?}", TypeMeta { kind: String::from("primitive"), name: String::from("i64"), fqn: String::from("i64"), family_name: String::from("i64"), family_fqn: String::from("i64"), args: Vec::<TypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() });
    println!("{:?}", TypeMeta { kind: String::from("primitive"), name: String::from("bool"), fqn: String::from("bool"), family_name: String::from("bool"), family_fqn: String::from("bool"), args: Vec::<TypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() });
    println!("{:?}", TypeMeta { kind: String::from("array"), name: String::from("[i64]"), fqn: String::from("[i64]"), family_name: String::from("array"), family_fqn: String::from("array"), args: vec![TypeMeta { kind: String::from("primitive"), name: String::from("i64"), fqn: String::from("i64"), family_name: String::from("i64"), family_fqn: String::from("i64"), args: Vec::<TypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }], is_named: false, is_bounded: false, infer_slots: Vec::<String>::new() });
    println!("{:?}", TypeMeta { kind: String::from("dict"), name: String::from("dict<String, i64>"), fqn: String::from("dict<String, i64>"), family_name: String::from("dict"), family_fqn: String::from("dict"), args: vec![TypeMeta { kind: String::from("primitive"), name: String::from("String"), fqn: String::from("String"), family_name: String::from("String"), family_fqn: String::from("String"), args: Vec::<TypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, TypeMeta { kind: String::from("primitive"), name: String::from("i64"), fqn: String::from("i64"), family_name: String::from("i64"), family_fqn: String::from("i64"), args: Vec::<TypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }], is_named: false, is_bounded: false, infer_slots: Vec::<String>::new() });
    println!("{:?}", TypeMeta { kind: String::from("set"), name: String::from("set<i64>"), fqn: String::from("set<i64>"), family_name: String::from("set"), family_fqn: String::from("set"), args: vec![TypeMeta { kind: String::from("primitive"), name: String::from("i64"), fqn: String::from("i64"), family_name: String::from("i64"), family_fqn: String::from("i64"), args: Vec::<TypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }], is_named: false, is_bounded: false, infer_slots: Vec::<String>::new() });
    println!("{:?}", TypeMeta { kind: String::from("tuple"), name: String::from("(i64, String, bool)"), fqn: String::from("(i64, String, bool)"), family_name: String::from("tuple"), family_fqn: String::from("tuple"), args: vec![TypeMeta { kind: String::from("primitive"), name: String::from("i64"), fqn: String::from("i64"), family_name: String::from("i64"), family_fqn: String::from("i64"), args: Vec::<TypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, TypeMeta { kind: String::from("primitive"), name: String::from("String"), fqn: String::from("String"), family_name: String::from("String"), family_fqn: String::from("String"), args: Vec::<TypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, TypeMeta { kind: String::from("primitive"), name: String::from("bool"), fqn: String::from("bool"), family_name: String::from("bool"), family_fqn: String::from("bool"), args: Vec::<TypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }], is_named: false, is_bounded: false, infer_slots: Vec::<String>::new() });
    println!("{}", String::from("callable"));
    println!("{:?}", TypeMeta { kind: String::from("channel"), name: String::from("channel<i64>"), fqn: String::from("channel<i64>"), family_name: String::from("channel"), family_fqn: String::from("channel"), args: vec![TypeMeta { kind: String::from("primitive"), name: String::from("i64"), fqn: String::from("i64"), family_name: String::from("i64"), family_fqn: String::from("i64"), args: Vec::<TypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }], is_named: false, is_bounded: false, infer_slots: Vec::<String>::new() });
    println!("{}", String::from("i64"));
    println!("{}", false);
    println!("{}", String::from("ChannelMeta"));
    println!("{:?}", TypeMeta { kind: String::from("channel"), name: String::from("channel<String>"), fqn: String::from("channel<String>"), family_name: String::from("channel"), family_fqn: String::from("channel"), args: vec![TypeMeta { kind: String::from("primitive"), name: String::from("String"), fqn: String::from("String"), family_name: String::from("String"), family_fqn: String::from("String"), args: Vec::<TypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }], is_named: false, is_bounded: true, infer_slots: Vec::<String>::new() });
    println!("{}", String::from("String"));
    println!("{}", true);
    println!("{}", String::from("ChannelMeta"));
    println!("{}", String::from("i64"));
    println!("{}", String::from("String"));
    println!("{}", String::from("ComponentOrder"));
    println!("{:?}", TypeMeta { kind: String::from("struct"), name: String::from("Pair<i64, String>"), fqn: String::from("metadata/02_type_meta/Pair<i64, String>"), family_name: String::from("Pair"), family_fqn: String::from("metadata/02_type_meta/Pair"), args: vec![TypeMeta { kind: String::from("primitive"), name: String::from("i64"), fqn: String::from("i64"), family_name: String::from("i64"), family_fqn: String::from("i64"), args: Vec::<TypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, TypeMeta { kind: String::from("primitive"), name: String::from("String"), fqn: String::from("String"), family_name: String::from("String"), family_fqn: String::from("String"), args: Vec::<TypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }], is_named: true, is_bounded: false, infer_slots: vec![String::from("x"), String::from("y")] });
    println!("{:?}", vec![TypeMeta { kind: String::from("primitive"), name: String::from("i64"), fqn: String::from("i64"), family_name: String::from("i64"), family_fqn: String::from("i64"), args: Vec::<TypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, TypeMeta { kind: String::from("primitive"), name: String::from("String"), fqn: String::from("String"), family_name: String::from("String"), family_fqn: String::from("String"), args: Vec::<TypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }]);
    println!("{:?}", vec![String::from("x"), String::from("y")]);
    println!("{:?}", TypeMeta { kind: String::from("struct"), name: String::from("Node"), fqn: String::from("metadata/02_type_meta/Node"), family_name: String::from("Node"), family_fqn: String::from("metadata/02_type_meta/Node"), args: Vec::<TypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() });
    println!("{:?}", TypeMeta { kind: String::from("struct"), name: String::from("Node"), fqn: String::from("metadata/02_type_meta/Node"), family_name: String::from("Node"), family_fqn: String::from("metadata/02_type_meta/Node"), args: Vec::<TypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() });
    println!("{:?}", vec![FieldMeta { kind: String::from("field"), name: String::from("version"), fqn: String::from("metadata/02_type_meta/Node/version"), module_fqn: String::from("metadata/02_type_meta"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/02_type_meta.zn"), line_num: 11, is_public: true, value_type: TypeMeta { kind: String::from("primitive"), name: String::from("i64"), fqn: String::from("i64"), family_name: String::from("i64"), family_fqn: String::from("i64"), args: Vec::<TypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, index: 0, is_const: true, has_default: true, is_declared: false, source_component_fqn: String::from("metadata/02_type_meta/Base") }, FieldMeta { kind: String::from("field"), name: String::from("name"), fqn: String::from("metadata/02_type_meta/Node/name"), module_fqn: String::from("metadata/02_type_meta"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/02_type_meta.zn"), line_num: 12, is_public: true, value_type: TypeMeta { kind: String::from("primitive"), name: String::from("String"), fqn: String::from("String"), family_name: String::from("String"), family_fqn: String::from("String"), args: Vec::<TypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, index: 1, is_const: false, has_default: false, is_declared: false, source_component_fqn: String::from("metadata/02_type_meta/Base") }, FieldMeta { kind: String::from("field"), name: String::from("level"), fqn: String::from("metadata/02_type_meta/Node/level"), module_fqn: String::from("metadata/02_type_meta"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/02_type_meta.zn"), line_num: 16, is_public: true, value_type: TypeMeta { kind: String::from("primitive"), name: String::from("i64"), fqn: String::from("i64"), family_name: String::from("i64"), family_fqn: String::from("i64"), args: Vec::<TypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, index: 2, is_const: false, has_default: false, is_declared: false, source_component_fqn: String::from("metadata/02_type_meta/Detail") }, FieldMeta { kind: String::from("field"), name: String::from("enabled"), fqn: String::from("metadata/02_type_meta/Node/enabled"), module_fqn: String::from("metadata/02_type_meta"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/02_type_meta.zn"), line_num: 24, is_public: true, value_type: TypeMeta { kind: String::from("primitive"), name: String::from("bool"), fqn: String::from("bool"), family_name: String::from("bool"), family_fqn: String::from("bool"), args: Vec::<TypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, index: 3, is_const: false, has_default: false, is_declared: true, source_component_fqn: String::from("") }]);
    println!("{:?}", FieldMeta { kind: String::from("field"), name: String::from("version"), fqn: String::from("metadata/02_type_meta/Node/version"), module_fqn: String::from("metadata/02_type_meta"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/02_type_meta.zn"), line_num: 11, is_public: true, value_type: TypeMeta { kind: String::from("primitive"), name: String::from("i64"), fqn: String::from("i64"), family_name: String::from("i64"), family_fqn: String::from("i64"), args: Vec::<TypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, index: 0, is_const: true, has_default: true, is_declared: false, source_component_fqn: String::from("metadata/02_type_meta/Base") });
    println!("{}", String::from("Node"));
    println!("{:?}", vec![MethodMeta { kind: String::from("method"), name: String::from("scale"), fqn: String::from("metadata/02_type_meta/Node/scale"), module_fqn: String::from("metadata/02_type_meta"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/02_type_meta.zn"), line_num: 18, is_public: true, params: vec![MethodParameterMeta { kind: String::from("parameter"), name: String::from("multiplier"), fqn: String::from("metadata/02_type_meta/Node/scale/multiplier"), module_fqn: String::from("metadata/02_type_meta"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/02_type_meta.zn"), line_num: 18, is_public: false, index: 0, value_type: TypeMeta { kind: String::from("primitive"), name: String::from("i64"), fqn: String::from("i64"), family_name: String::from("i64"), family_fqn: String::from("i64"), args: Vec::<TypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, declared_type: TypeMeta { kind: String::from("primitive"), name: String::from("i64"), fqn: String::from("i64"), family_name: String::from("i64"), family_fqn: String::from("i64"), args: Vec::<TypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, has_declared_type: true, has_default: false }], return_type: TypeMeta { kind: String::from("primitive"), name: String::from("i64"), fqn: String::from("i64"), family_name: String::from("i64"), family_fqn: String::from("i64"), args: Vec::<TypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, is_async: false, is_static: false, is_declared: false }]);
    println!("{:?}", MethodMeta { kind: String::from("method"), name: String::from("scale"), fqn: String::from("metadata/02_type_meta/Node/scale"), module_fqn: String::from("metadata/02_type_meta"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/02_type_meta.zn"), line_num: 18, is_public: true, params: vec![MethodParameterMeta { kind: String::from("parameter"), name: String::from("multiplier"), fqn: String::from("metadata/02_type_meta/Node/scale/multiplier"), module_fqn: String::from("metadata/02_type_meta"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/02_type_meta.zn"), line_num: 18, is_public: false, index: 0, value_type: TypeMeta { kind: String::from("primitive"), name: String::from("i64"), fqn: String::from("i64"), family_name: String::from("i64"), family_fqn: String::from("i64"), args: Vec::<TypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, declared_type: TypeMeta { kind: String::from("primitive"), name: String::from("i64"), fqn: String::from("i64"), family_name: String::from("i64"), family_fqn: String::from("i64"), args: Vec::<TypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, has_declared_type: true, has_default: false }], return_type: TypeMeta { kind: String::from("primitive"), name: String::from("i64"), fqn: String::from("i64"), family_name: String::from("i64"), family_fqn: String::from("i64"), args: Vec::<TypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, is_async: false, is_static: false, is_declared: false });
    println!("{}", String::from("Node"));
    println!("{:?}", vec![TypeMeta { kind: String::from("struct"), name: String::from("Base"), fqn: String::from("metadata/02_type_meta/Base"), family_name: String::from("Base"), family_fqn: String::from("metadata/02_type_meta/Base"), args: Vec::<TypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, TypeMeta { kind: String::from("struct"), name: String::from("Detail"), fqn: String::from("metadata/02_type_meta/Detail"), family_name: String::from("Detail"), family_fqn: String::from("metadata/02_type_meta/Detail"), args: Vec::<TypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }]);
    println!("{:?}", vec![TypeMeta { kind: String::from("struct"), name: String::from("Base"), fqn: String::from("metadata/02_type_meta/Base"), family_name: String::from("Base"), family_fqn: String::from("metadata/02_type_meta/Base"), args: Vec::<TypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, TypeMeta { kind: String::from("struct"), name: String::from("Detail"), fqn: String::from("metadata/02_type_meta/Detail"), family_name: String::from("Detail"), family_fqn: String::from("metadata/02_type_meta/Detail"), args: Vec::<TypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }]);
    println!("{:?}", vec![TypeMeta { kind: String::from("struct"), name: String::from("Base"), fqn: String::from("metadata/02_type_meta/Base"), family_name: String::from("Base"), family_fqn: String::from("metadata/02_type_meta/Base"), args: Vec::<TypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, TypeMeta { kind: String::from("struct"), name: String::from("Detail"), fqn: String::from("metadata/02_type_meta/Detail"), family_name: String::from("Detail"), family_fqn: String::from("metadata/02_type_meta/Detail"), args: Vec::<TypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }]);
    println!("{:?}", TypeMeta { kind: String::from("enum"), name: String::from("Mode"), fqn: String::from("metadata/02_type_meta/Mode"), family_name: String::from("Mode"), family_fqn: String::from("metadata/02_type_meta/Mode"), args: Vec::<TypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() });
    println!("{:?}", Vec::<FieldMeta>::new());
    println!("{:?}", vec![MethodMeta { kind: String::from("method"), name: String::from("static_note"), fqn: String::from("metadata/02_type_meta/Mode/static_note"), module_fqn: String::from("metadata/02_type_meta"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/02_type_meta.zn"), line_num: 5, is_public: true, params: Vec::<MethodParameterMeta>::new(), return_type: TypeMeta { kind: String::from("primitive"), name: String::from("String"), fqn: String::from("String"), family_name: String::from("String"), family_fqn: String::from("String"), args: Vec::<TypeMeta>::new(), is_named: true, is_bounded: false, infer_slots: Vec::<String>::new() }, is_async: false, is_static: true, is_declared: true }]);
    println!("{:?}", vec![VariantMeta { kind: String::from("variant"), name: String::from("Auto"), fqn: String::from("metadata/02_type_meta/Mode/Auto"), module_fqn: String::from("metadata/02_type_meta"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/02_type_meta.zn"), line_num: 2, is_public: true, index: 0 }, VariantMeta { kind: String::from("variant"), name: String::from("Manual"), fqn: String::from("metadata/02_type_meta/Mode/Manual"), module_fqn: String::from("metadata/02_type_meta"), file: String::from("/Users/eric/code/zinc/test/zinc_source/metadata/02_type_meta.zn"), line_num: 3, is_public: true, index: 1 }]);
    println!("{:?}", Vec::<FieldMeta>::new());
    println!("{:?}", Vec::<MethodMeta>::new());
    println!("{:?}", Vec::<TypeMeta>::new());
    println!("{}", String::from("Result"));
    println!("{}", String::from("i64"));
    println!("{}", String::from("String"));
    println!("{}", String::from("Option"));
    println!("{}", String::from("String"));
}