"""Decorator metadata shared by Zinc semantic analysis and code generation."""

from dataclasses import dataclass, field
from typing import Any

from antlr4 import ParserRuleContext
from zinc.ast.types import CallableTypeInfo


@dataclass(frozen=True)
class DecoratorInfo:
    """Syntactic information for one declaration decorator."""

    path: tuple[str, ...]
    has_call: bool
    argument_list_ctx: ParserRuleContext | None
    ctx: ParserRuleContext
    line_num: int
    source_interval: tuple[int, int]

    @property
    def display_name(self) -> str:
        """Return the user-facing decorator path."""
        return ".".join(self.path)


@dataclass
class ResolvedDecoratorApplication:
    """A type-checked decorator application for one function specialization."""

    info: DecoratorInfo
    kind: str
    result_callable_info: CallableTypeInfo
    decorator_mangled_name: str | None = None
    decorator_bound_args: list[Any] = field(default_factory=list)
    target_parameter_index: int | None = None
    factory_mangled_name: str | None = None
    factory_bound_args: list[Any] = field(default_factory=list)
    factory_callable_info: CallableTypeInfo | None = None


def decorators_from_ctx(ctx: Any) -> list[DecoratorInfo]:
    """Extract decorator metadata from a generated parser context."""
    getter = getattr(ctx, "decorator", None)
    if getter is None:
        return []
    decorators = []
    for decorator_ctx in getter():
        path = tuple(part.getText() for part in decorator_ctx.qualifiedName().IDENTIFIER())
        has_call = decorator_ctx.getChildCount() > 2
        decorators.append(
            DecoratorInfo(
                path=path,
                has_call=has_call,
                argument_list_ctx=decorator_ctx.argumentList(),
                ctx=decorator_ctx,
                line_num=decorator_ctx.start.line if decorator_ctx.start is not None else 0,
                source_interval=decorator_ctx.getSourceInterval(),
            )
        )
    return decorators
