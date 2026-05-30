#![allow(non_camel_case_types)]

#[cfg(feature = "channel")]
mod channel;
#[cfg(feature = "context")]
mod context;
#[cfg(feature = "metadata")]
mod metadata;

#[cfg(feature = "channel")]
pub use channel::{__ZincChannel, __ZincTryRecv, __ZincTrySend};
#[cfg(feature = "context")]
pub use context::__ZincContext;
#[cfg(feature = "metadata")]
pub use metadata::{
    __ZincBuiltinMeta, __ZincComponentOrder, __ZincConstMeta, __ZincEnumMeta, __ZincFieldMeta,
    __ZincFunctionMeta, __ZincFunctionParameterMeta, __ZincMethodMeta, __ZincMethodParameterMeta, __ZincStructMeta,
    __ZincTypeMeta, __ZincVariableMeta, __ZincVariantMeta,
};
