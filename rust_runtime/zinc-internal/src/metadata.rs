#[derive(Clone, Debug, Default, PartialEq)]
pub struct TypeMeta {
    pub kind: String,
    pub name: String,
    pub fqn: String,
    pub family_name: String,
    pub family_fqn: String,
    pub args: Vec<TypeMeta>,
    pub is_named: bool,
    pub is_bounded: bool,
    pub infer_slots: Vec<String>,
}

#[derive(Clone, Debug, Default, PartialEq)]
pub struct StructMeta {
    pub kind: String,
    pub name: String,
    pub fqn: String,
    pub module_fqn: String,
    pub file: String,
    pub line_num: u32,
    pub is_public: bool,
    pub type_info: TypeMeta,
}

#[derive(Clone, Debug, Default, PartialEq)]
pub struct EnumMeta {
    pub kind: String,
    pub name: String,
    pub fqn: String,
    pub module_fqn: String,
    pub file: String,
    pub line_num: u32,
    pub is_public: bool,
    pub type_info: TypeMeta,
}

#[derive(Clone, Debug, Default, PartialEq)]
pub struct VariantMeta {
    pub kind: String,
    pub name: String,
    pub fqn: String,
    pub module_fqn: String,
    pub file: String,
    pub line_num: u32,
    pub is_public: bool,
    pub index: u32,
}

#[derive(Clone, Debug, Default, PartialEq)]
pub struct FieldMeta {
    pub kind: String,
    pub name: String,
    pub fqn: String,
    pub module_fqn: String,
    pub file: String,
    pub line_num: u32,
    pub is_public: bool,
    pub value_type: TypeMeta,
    pub index: u32,
    pub is_const: bool,
    pub has_default: bool,
    pub is_declared: bool,
    pub source_component_fqn: String,
}

#[derive(Clone, Debug, Default, PartialEq)]
pub struct FunctionParameterMeta {
    pub kind: String,
    pub name: String,
    pub fqn: String,
    pub module_fqn: String,
    pub file: String,
    pub line_num: u32,
    pub is_public: bool,
    pub index: u32,
    pub value_type: TypeMeta,
    pub declared_type: TypeMeta,
    pub has_declared_type: bool,
    pub has_default: bool,
}

#[derive(Clone, Debug, Default, PartialEq)]
pub struct MethodParameterMeta {
    pub kind: String,
    pub name: String,
    pub fqn: String,
    pub module_fqn: String,
    pub file: String,
    pub line_num: u32,
    pub is_public: bool,
    pub index: u32,
    pub value_type: TypeMeta,
    pub declared_type: TypeMeta,
    pub has_declared_type: bool,
    pub has_default: bool,
}

#[derive(Clone, Debug, Default, PartialEq)]
pub struct FunctionMeta {
    pub kind: String,
    pub name: String,
    pub fqn: String,
    pub module_fqn: String,
    pub file: String,
    pub line_num: u32,
    pub is_public: bool,
    pub params: Vec<FunctionParameterMeta>,
    pub return_type: TypeMeta,
    pub is_async: bool,
}

#[derive(Clone, Debug, Default, PartialEq)]
pub struct BuiltinMeta {
    pub kind: String,
    pub name: String,
    pub fqn: String,
    pub module_fqn: String,
    pub file: String,
    pub line_num: u32,
    pub is_public: bool,
    pub params: Vec<FunctionParameterMeta>,
    pub return_type: TypeMeta,
    pub is_async: bool,
}

#[derive(Clone, Debug, Default, PartialEq)]
pub struct MethodMeta {
    pub kind: String,
    pub name: String,
    pub fqn: String,
    pub module_fqn: String,
    pub file: String,
    pub line_num: u32,
    pub is_public: bool,
    pub params: Vec<MethodParameterMeta>,
    pub return_type: TypeMeta,
    pub is_async: bool,
    pub is_static: bool,
    pub is_declared: bool,
}

#[derive(Clone, Debug, Default, PartialEq)]
pub struct VariableMeta {
    pub kind: String,
    pub name: String,
    pub fqn: String,
    pub module_fqn: String,
    pub file: String,
    pub line_num: u32,
    pub is_public: bool,
    pub value_type: TypeMeta,
    pub has_declared_type: bool,
    pub is_mutated: bool,
    pub is_shadow: bool,
}

#[derive(Clone, Debug, Default, PartialEq)]
pub struct ConstMeta {
    pub kind: String,
    pub name: String,
    pub fqn: String,
    pub module_fqn: String,
    pub file: String,
    pub line_num: u32,
    pub is_public: bool,
    pub value_type: TypeMeta,
    pub value_text: String,
}

#[derive(Clone, Debug, PartialEq)]
pub enum ComponentOrder {
    DepthFirst,
    BreadthFirst,
    Topological,
}
