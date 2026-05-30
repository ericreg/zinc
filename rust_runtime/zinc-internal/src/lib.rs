#[cfg(feature = "channel")]
mod channel;
#[cfg(feature = "context")]
mod context;
#[cfg(feature = "metadata")]
mod metadata;

#[cfg(feature = "channel")]
pub use channel::{Channel, TryRecv, TrySend};
#[cfg(feature = "context")]
pub use context::Context;
#[cfg(feature = "metadata")]
pub use metadata::{
    BuiltinMeta, ComponentOrder, ConstMeta, EnumMeta, FieldMeta, FunctionMeta,
    FunctionParameterMeta, MethodMeta, MethodParameterMeta, StructMeta, TypeMeta, VariableMeta,
    VariantMeta,
};
