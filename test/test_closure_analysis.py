"""Focused unit tests for closure analysis metadata."""

from pathlib import Path

from zinc.atlas import AtlasBuilder
from zinc.modules import build_module_graph
from zinc.symbols import SymbolTableVisitor


def resolve_source(tmp_path: Path, source: str) -> SymbolTableVisitor:
    """Resolve a small Zinc package and return the populated symbol visitor."""
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()
    (pkg_dir / "pkg.toml").write_text(
        "\n".join([
            "[package]",
            'name = "tmp"',
            'version = "0.1.0"',
        ])
    )
    entry = pkg_dir / "main.zn"
    entry.write_text(source)
    module_graph = build_module_graph(entry)
    atlas = AtlasBuilder(module_graph).build()
    visitor = SymbolTableVisitor(atlas)
    visitor.resolve()
    return visitor


def test_lambda_capture_order_is_stable(tmp_path: Path) -> None:
    """Capture ordering should follow lexical first-use order."""
    visitor = resolve_source(
        tmp_path,
        """
        fn main() {
            x = 1
            y = 2
            f = fn(z) {
                return x + y + z + x
            }
            print(f(3))
        }
        """,
    )

    closure = next(iter(visitor.lexical_functions.values()))
    assert [capture.name for capture in closure.captures] == ["x", "y"]


def test_zero_capture_lambda_keeps_empty_env(tmp_path: Path) -> None:
    """No-capture lambdas should still resolve as closures with no captures."""
    visitor = resolve_source(
        tmp_path,
        """
        fn main() {
            f = fn(x) {
                return x + 1
            }
            print(f(2))
        }
        """,
    )

    closure = next(iter(visitor.lexical_functions.values()))
    assert closure.captures == []


def test_nested_named_function_captures_outer_parameter(tmp_path: Path) -> None:
    """Nested named functions should capture parameters from enclosing scopes."""
    visitor = resolve_source(
        tmp_path,
        """
        fn make_adder(base) {
            fn add(x) {
                return base + x
            }
            return add
        }

        fn main() {
            add2 = make_adder(2)
            print(add2(5))
        }
        """,
    )

    add_info = next(info for info in visitor.lexical_functions.values() if info.display_name == "add")
    assert [capture.name for capture in add_info.captures] == ["base"]


def test_closure_transport_rejects_captured_bound_method(tmp_path: Path) -> None:
    """Closures that capture bound-method callable values are not transport safe."""
    visitor = resolve_source(
        tmp_path,
        """
        struct Counter {
            count: 0

            fn inc() {
                self.count = self.count + 1
            }
        }

        fn main() {
            c = Counter {}
            step = c.inc
            f = fn() {
                step()
            }
        }
        """,
    )

    closure = next(iter(visitor.lexical_functions.values()))
    callable_info = visitor._callable_info_from_lexical_function(closure)
    assert not visitor._callable_is_transport_safe(callable_info)

