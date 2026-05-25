"""Focused unit tests for anonymous struct type metadata."""

from zinc.ast.types import (
    AnonymousStructFieldInfo,
    AnonymousStructTypeInfo,
    ArrayTypeInfo,
    BaseType,
    CallableTarget,
    CallableTypeInfo,
    ChannelTypeInfo,
    DictTypeInfo,
    SetTypeInfo,
    TupleTypeInfo,
    value_type_key,
    value_type_suffix,
)


def anon_field(
    name: str,
    resolved_type: BaseType,
    *,
    array_info: ArrayTypeInfo | None = None,
    dict_info: DictTypeInfo | None = None,
    set_info: SetTypeInfo | None = None,
    tuple_info: TupleTypeInfo | None = None,
    callable_info: CallableTypeInfo | None = None,
    struct_qualified_name: str | None = None,
    anonymous_struct_info: AnonymousStructTypeInfo | None = None,
) -> AnonymousStructFieldInfo:
    """Build a small anonymous-struct field descriptor for tests."""
    return AnonymousStructFieldInfo(
        name=name,
        resolved_type=resolved_type,
        array_info=array_info,
        dict_info=dict_info,
        set_info=set_info,
        tuple_info=tuple_info,
        callable_info=callable_info,
        struct_qualified_name=struct_qualified_name,
        anonymous_struct_info=anonymous_struct_info,
    )


def test_structural_key_ignores_field_order() -> None:
    """Exact anonymous-struct identity should ignore declaration order."""
    left = AnonymousStructTypeInfo(
        fields=[
            anon_field("x", BaseType.INTEGER),
            anon_field("name", BaseType.STRING),
        ]
    )
    right = AnonymousStructTypeInfo(
        fields=[
            anon_field("name", BaseType.STRING),
            anon_field("x", BaseType.INTEGER),
        ]
    )

    assert left.structural_key() == right.structural_key()
    assert left.to_rust_type_suffix() == right.to_rust_type_suffix()


def test_empty_anonymous_struct_shape_is_stable() -> None:
    """Empty anonymous structs should have a canonical, deduplicated identity."""
    empty = AnonymousStructTypeInfo()

    assert empty.structural_key() == ()
    assert empty.to_rust_type_suffix() == "AnonStruct_empty"
    assert empty.rust_type_name() == "__ZincAnonStruct_AnonStruct_empty"


def test_structural_key_changes_for_nested_shape_changes() -> None:
    """Nested anonymous fields participate recursively in exact shape matching."""
    meta_a = AnonymousStructTypeInfo(
        fields=[
            anon_field("author", BaseType.STRING),
            anon_field("active", BaseType.BOOLEAN),
        ]
    )
    meta_b = AnonymousStructTypeInfo(
        fields=[
            anon_field("author", BaseType.STRING),
            anon_field("score", BaseType.INTEGER),
        ]
    )
    post_a = AnonymousStructTypeInfo(fields=[anon_field("meta", BaseType.STRUCT, anonymous_struct_info=meta_a)])
    post_b = AnonymousStructTypeInfo(fields=[anon_field("meta", BaseType.STRUCT, anonymous_struct_info=meta_b)])

    assert post_a.structural_key() != post_b.structural_key()


def test_callable_signature_ignores_anonymous_field_order() -> None:
    """Callable signatures should treat anonymous struct params structurally."""
    left_payload = AnonymousStructTypeInfo(
        fields=[
            anon_field("id", BaseType.INTEGER),
            anon_field("label", BaseType.STRING),
        ]
    )
    right_payload = AnonymousStructTypeInfo(
        fields=[
            anon_field("label", BaseType.STRING),
            anon_field("id", BaseType.INTEGER),
        ]
    )
    left = CallableTypeInfo(
        param_types=[BaseType.STRUCT],
        param_anonymous_struct_infos={0: left_payload},
        return_type=BaseType.BOOLEAN,
    )
    right = CallableTypeInfo(
        param_types=[BaseType.STRUCT],
        param_anonymous_struct_infos={0: right_payload},
        return_type=BaseType.BOOLEAN,
    )

    assert left.structural_key() == right.structural_key()
    assert left.to_rust_type_suffix() == right.to_rust_type_suffix()


def test_anonymous_struct_copy_is_deep_for_nested_metadata() -> None:
    """Copying anonymous-struct metadata should not alias nested shapes."""
    point = AnonymousStructTypeInfo(
        fields=[
            anon_field("x", BaseType.INTEGER),
            anon_field("y", BaseType.INTEGER),
        ]
    )
    wrapper = AnonymousStructTypeInfo(
        fields=[
            anon_field(
                "points",
                BaseType.ARRAY,
                array_info=ArrayTypeInfo(
                    element_type=BaseType.STRUCT,
                    element_anonymous_struct_info=point,
                ),
            )
        ]
    )

    copied = wrapper.copy()
    copied.fields[0].array_info.element_anonymous_struct_info.fields[0].name = "z"

    assert wrapper.fields[0].array_info.element_anonymous_struct_info.fields[0].name == "x"
    assert copied.fields[0].array_info.element_anonymous_struct_info.fields[0].name == "z"


def test_callable_copy_is_deep_for_anonymous_struct_shapes() -> None:
    """Callable copies should not alias nested anonymous param/return shapes."""
    payload = AnonymousStructTypeInfo(
        fields=[
            anon_field("id", BaseType.INTEGER),
            anon_field("name", BaseType.STRING),
        ]
    )
    callable_info = CallableTypeInfo(
        param_types=[BaseType.STRUCT],
        param_anonymous_struct_infos={0: payload},
        return_type=BaseType.STRUCT,
        return_anonymous_struct_info=payload,
    )

    copied = callable_info.copy()
    copied.param_anonymous_struct_infos[0].fields[0].name = "uuid"
    copied.return_anonymous_struct_info.fields[1].name = "title"

    assert callable_info.param_anonymous_struct_infos[0].fields[0].name == "id"
    assert callable_info.return_anonymous_struct_info.fields[1].name == "name"
    assert copied.param_anonymous_struct_infos[0].fields[0].name == "uuid"
    assert copied.return_anonymous_struct_info.fields[1].name == "title"


def test_channel_copy_is_deep_for_anonymous_struct_payload() -> None:
    """Channel copies should isolate anonymous payload metadata."""
    payload = AnonymousStructTypeInfo(
        fields=[
            anon_field("id", BaseType.INTEGER),
            anon_field("ready", BaseType.BOOLEAN),
        ]
    )
    channel_info = ChannelTypeInfo(
        element_type=BaseType.STRUCT,
        element_anonymous_struct_info=payload,
        is_bounded=True,
    )

    copied = channel_info.copy()
    copied.element_anonymous_struct_info.fields[1].name = "sent"

    assert channel_info.element_anonymous_struct_info.fields[1].name == "ready"
    assert copied.element_anonymous_struct_info.fields[1].name == "sent"
    assert copied.to_rust_type_suffix().startswith("BoundedChannel_AnonStruct_")


def test_named_and_anonymous_struct_keys_and_suffixes_stay_distinct() -> None:
    """Nominal named structs must remain distinct from anonymous shapes."""
    anon = AnonymousStructTypeInfo(fields=[anon_field("x", BaseType.INTEGER)])
    named_key = value_type_key(BaseType.STRUCT, struct_qualified_name="pkg/mod::Point")
    anon_key = value_type_key(BaseType.STRUCT, anonymous_struct_info=anon)

    assert named_key != anon_key
    assert value_type_suffix(BaseType.STRUCT, struct_qualified_name="pkg/mod::Point").startswith("Struct_")
    assert value_type_suffix(BaseType.STRUCT, anonymous_struct_info=anon).startswith("AnonStruct_")


def test_callable_signatures_with_anonymous_structs_merge_by_shape_not_target() -> None:
    """Callable structural equality should include anonymous struct params and returns."""
    payload = AnonymousStructTypeInfo(
        fields=[
            anon_field("id", BaseType.INTEGER),
            anon_field("ok", BaseType.BOOLEAN),
        ]
    )
    first = CallableTypeInfo(
        param_types=[BaseType.STRUCT],
        param_anonymous_struct_infos={0: payload},
        return_type=BaseType.STRUCT,
        return_anonymous_struct_info=payload,
        targets=(
            CallableTarget(
                kind="function",
                qualified_name="pkg::first",
                display_name="first",
            ),
        ),
    )
    second = CallableTypeInfo(
        param_types=[BaseType.STRUCT],
        param_anonymous_struct_infos={0: payload.copy()},
        return_type=BaseType.STRUCT,
        return_anonymous_struct_info=payload.copy(),
        targets=(
            CallableTarget(
                kind="function",
                qualified_name="pkg::second",
                display_name="second",
            ),
        ),
    )

    merged = first.merge_targets_from(second)

    assert first.structural_key() == second.structural_key()
    assert len(merged.targets) == 2
    assert "AnonStruct" in merged.to_rust_type_suffix()


def test_container_keys_change_for_nested_anonymous_shape_changes() -> None:
    """Nested anonymous shape changes should flow into container identity."""
    point = AnonymousStructTypeInfo(
        fields=[
            anon_field("x", BaseType.INTEGER),
            anon_field("y", BaseType.INTEGER),
        ]
    )
    labeled_point = AnonymousStructTypeInfo(
        fields=[
            anon_field("x", BaseType.INTEGER),
            anon_field("label", BaseType.STRING),
        ]
    )
    point_tuple = TupleTypeInfo(
        element_types=[BaseType.STRUCT],
        element_anonymous_struct_infos={0: point},
    )
    labeled_tuple = TupleTypeInfo(
        element_types=[BaseType.STRUCT],
        element_anonymous_struct_infos={0: labeled_point},
    )

    assert value_type_key(BaseType.TUPLE, tuple_info=point_tuple) != value_type_key(
        BaseType.TUPLE,
        tuple_info=labeled_tuple,
    )
    assert value_type_suffix(BaseType.TUPLE, tuple_info=point_tuple) != value_type_suffix(
        BaseType.TUPLE,
        tuple_info=labeled_tuple,
    )


def test_container_suffixes_embed_anonymous_struct_shapes() -> None:
    """Container metadata should preserve anonymous struct identity in mangling."""
    point = AnonymousStructTypeInfo(
        fields=[
            anon_field("x", BaseType.INTEGER),
            anon_field("y", BaseType.INTEGER),
        ]
    )
    array_info = ArrayTypeInfo(
        element_type=BaseType.STRUCT,
        element_anonymous_struct_info=point,
    )
    dict_info = DictTypeInfo(
        key_type=BaseType.STRING,
        value_type=BaseType.STRUCT,
        value_anonymous_struct_info=point,
    )
    set_info = SetTypeInfo(
        element_type=BaseType.STRUCT,
        element_anonymous_struct_info=point,
    )
    tuple_info = TupleTypeInfo(
        element_types=[BaseType.STRUCT, BaseType.INTEGER],
        element_anonymous_struct_infos={0: point},
    )
    channel_info = ChannelTypeInfo(
        element_type=BaseType.STRUCT,
        element_anonymous_struct_info=point,
    )

    assert "AnonStruct" in array_info.to_rust_type_suffix()
    assert "AnonStruct" in dict_info.to_rust_type_suffix()
    assert "AnonStruct" in set_info.to_rust_type_suffix()
    assert "AnonStruct" in tuple_info.to_rust_type_suffix()
    assert "AnonStruct" in channel_info.to_rust_type_suffix()
