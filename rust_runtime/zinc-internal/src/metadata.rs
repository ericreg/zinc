#[derive(Clone, Debug, Default, PartialEq)]
pub struct __ZincTypeMeta {
    pub kind: String,
    pub name: String,
    pub fqn: String,
    pub family_name: String,
    pub family_fqn: String,
    pub args: Vec<__ZincTypeMeta>,
    pub is_named: bool,
    pub is_bounded: bool,
    pub infer_slots: Vec<String>,
}

#[derive(Clone, Debug, Default, PartialEq)]
pub struct __ZincStructMeta {
    pub kind: String,
    pub name: String,
    pub fqn: String,
    pub module_fqn: String,
    pub file: String,
    pub line_num: u32,
    pub is_public: bool,
    pub type_info: __ZincTypeMeta,
}

#[derive(Clone, Debug, Default, PartialEq)]
pub struct __ZincEnumMeta {
    pub kind: String,
    pub name: String,
    pub fqn: String,
    pub module_fqn: String,
    pub file: String,
    pub line_num: u32,
    pub is_public: bool,
    pub type_info: __ZincTypeMeta,
}

#[derive(Clone, Debug, Default, PartialEq)]
pub struct __ZincVariantMeta {
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
pub struct __ZincFieldMeta {
    pub kind: String,
    pub name: String,
    pub fqn: String,
    pub module_fqn: String,
    pub file: String,
    pub line_num: u32,
    pub is_public: bool,
    pub value_type: __ZincTypeMeta,
    pub index: u32,
    pub is_const: bool,
    pub has_default: bool,
    pub is_declared: bool,
    pub source_component_fqn: String,
}

#[derive(Clone, Debug, Default, PartialEq)]
pub struct __ZincFunctionParameterMeta {
    pub kind: String,
    pub name: String,
    pub fqn: String,
    pub module_fqn: String,
    pub file: String,
    pub line_num: u32,
    pub is_public: bool,
    pub index: u32,
    pub value_type: __ZincTypeMeta,
    pub declared_type: __ZincTypeMeta,
    pub has_declared_type: bool,
    pub has_default: bool,
}

#[derive(Clone, Debug, Default, PartialEq)]
pub struct __ZincMethodParameterMeta {
    pub kind: String,
    pub name: String,
    pub fqn: String,
    pub module_fqn: String,
    pub file: String,
    pub line_num: u32,
    pub is_public: bool,
    pub index: u32,
    pub value_type: __ZincTypeMeta,
    pub declared_type: __ZincTypeMeta,
    pub has_declared_type: bool,
    pub has_default: bool,
}

#[derive(Clone, Debug, Default, PartialEq)]
pub struct __ZincFunctionMeta {
    pub kind: String,
    pub name: String,
    pub fqn: String,
    pub module_fqn: String,
    pub file: String,
    pub line_num: u32,
    pub is_public: bool,
    pub params: Vec<__ZincFunctionParameterMeta>,
    pub return_type: __ZincTypeMeta,
    pub is_async: bool,
}

#[derive(Clone, Debug, Default, PartialEq)]
pub struct __ZincBuiltinMeta {
    pub kind: String,
    pub name: String,
    pub fqn: String,
    pub module_fqn: String,
    pub file: String,
    pub line_num: u32,
    pub is_public: bool,
    pub params: Vec<__ZincFunctionParameterMeta>,
    pub return_type: __ZincTypeMeta,
    pub is_async: bool,
}

#[derive(Clone, Debug, Default, PartialEq)]
pub struct __ZincMethodMeta {
    pub kind: String,
    pub name: String,
    pub fqn: String,
    pub module_fqn: String,
    pub file: String,
    pub line_num: u32,
    pub is_public: bool,
    pub params: Vec<__ZincMethodParameterMeta>,
    pub return_type: __ZincTypeMeta,
    pub is_async: bool,
    pub is_static: bool,
    pub is_declared: bool,
}

#[derive(Clone, Debug, Default, PartialEq)]
pub struct __ZincVariableMeta {
    pub kind: String,
    pub name: String,
    pub fqn: String,
    pub module_fqn: String,
    pub file: String,
    pub line_num: u32,
    pub is_public: bool,
    pub value_type: __ZincTypeMeta,
    pub has_declared_type: bool,
    pub is_mutated: bool,
    pub is_shadow: bool,
}

#[derive(Clone, Debug, Default, PartialEq)]
pub struct __ZincConstMeta {
    pub kind: String,
    pub name: String,
    pub fqn: String,
    pub module_fqn: String,
    pub file: String,
    pub line_num: u32,
    pub is_public: bool,
    pub value_type: __ZincTypeMeta,
    pub value_text: String,
}

#[derive(Clone, Debug, PartialEq)]
pub enum __ZincComponentOrder {
    DepthFirst,
    BreadthFirst,
    Topological,
}
