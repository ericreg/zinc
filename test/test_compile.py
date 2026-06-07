"""Parameterized tests for Zinc compilation."""

import subprocess
import tempfile
from collections import Counter
from pathlib import Path

import click
import pytest
from zinc.atlas import AtlasBuilder
from zinc.codegen import CodeGenVisitor, RustProgram
from zinc.exceptions import ZincModuleError, ZincTypeError
from zinc.modules import build_module_graph
from zinc.struct_logging import configure_logging, get_logger
from zinc.symbols import SymbolTableVisitor

TEST_DIR = Path(__file__).parent
ZINC_SOURCE_DIR = TEST_DIR / "zinc_source"
COMPILE_ERROR_DIR = ZINC_SOURCE_DIR / "compile_errors"
RUST_SOURCE_DIR = TEST_DIR / "rust_source"
RUST_SRC_DIR = RUST_SOURCE_DIR / "src"  # Cargo src directory
OUTPUT_DIR = TEST_DIR / "output"
CARGO_TOML = RUST_SOURCE_DIR / "Cargo.toml"
RUNTIME_CRATE_PATH = "../../rust_runtime/zinc-internal"
NON_DETERMINISTIC_FOLDER = "non_deterministic"
COMPILE_ERROR_GROUPS = (
    "error_handling",
    "annotations",
    "metadata",
    "collections",
    "tuples",
    "iterations",
    "modules",
    "concurrency",
    "structs",
    "enums",
    "callables",
    "control_flow",
    "functions",
    "operators",
    "decorators",
    "rust_interop",
)
INLINE_RUNTIME_DEFINITIONS = (
    "enum TryRecv",
    "enum TrySend",
    "struct Channel",
    "struct Context",
)


def is_entry_fixture(relative: Path) -> bool:
    """Return True when a Zinc fixture should be treated as a test entrypoint."""
    if relative.parts and relative.parts[0] == "std":
        return False
    return all(not part.startswith("_") and "." not in part for part in relative.parts)


def get_test_cases() -> list[str]:
    """Discover test cases by finding .zn files in source directory (including subdirs).

    Returns relative paths without extension, e.g., "arithmetic" or "structs/01_basic_fields".
    """
    if not ZINC_SOURCE_DIR.exists():
        return []
    test_cases = []
    for f in ZINC_SOURCE_DIR.glob("**/*.zn"):
        # Get path relative to ZINC_SOURCE_DIR, without extension
        relative = f.relative_to(ZINC_SOURCE_DIR).with_suffix("")
        if relative.parts and relative.parts[0] == COMPILE_ERROR_DIR.name:
            continue
        if not is_entry_fixture(relative):
            continue
        test_cases.append(str(relative))
    return test_cases


def get_compile_error_files(group: str) -> list[Path]:
    """Discover compile-error Zinc fixtures for a specific group."""
    group_dir = COMPILE_ERROR_DIR / group
    if not group_dir.exists():
        return []
    return sorted(group_dir.glob("*.zn"))


def read_expected_error(source_path: Path) -> str:
    """Read the expected error regex from a compile-error fixture."""
    prefix = "// expected-error:"
    for line in source_path.read_text().splitlines():
        stripped = line.strip()
        if stripped.startswith(prefix):
            return stripped[len(prefix) :].strip()
    raise AssertionError(f"Missing {prefix} comment in {source_path}")


def generate_cargo_toml(test_paths: list[str], runtime_features: set[str] | None = None) -> str:
    """Generate Cargo.toml content with binary entries for each test.

    Args:
        test_paths: Relative paths without extension, e.g., "arithmetic" or "structs/01_basic_fields"
    """
    runtime_features = runtime_features or set()
    lines = [
        "[package]",
        'name = "zinc_tests"',
        'version = "0.1.0"',
        'edition = "2021"',
        "",
        "[dependencies]",
        'tokio = { version = "1", features = ["full"] }',
    ]
    if runtime_features:
        feature_list = ", ".join(f'"{feature}"' for feature in sorted(runtime_features))
        lines.append(f'zinc-internal = {{ path = "{RUNTIME_CRATE_PATH}", default-features = false, features = [{feature_list}] }}')
    lines.append("")

    for test_path in sorted(test_paths):
        # Binary name uses underscores for path separators (e.g., "structs_01_basic_fields")
        bin_name = test_path.replace("/", "_")
        lines.extend(
            [
                "[[bin]]",
                f'name = "{bin_name}"',
                f'path = "src/{test_path}.rs"',
                "",
            ]
        )

    # Add run_all binary for main.rs if it exists
    if (RUST_SRC_DIR / "main.rs").exists():
        lines.extend(
            [
                "[[bin]]",
                'name = "run_all"',
                'path = "src/main.rs"',
                "",
            ]
        )

    return "\n".join(lines)


def compile_zinc_program(source_path: Path) -> RustProgram:
    """Compile a Zinc entry file to a structured Rust program."""
    module_graph = build_module_graph(source_path)
    atlas = AtlasBuilder(module_graph).build()
    symbol_visitor = SymbolTableVisitor(atlas)
    symbols = symbol_visitor.resolve()
    codegen = CodeGenVisitor(
        atlas,
        symbols,
        symbol_visitor.specialization_map,
        symbol_visitor._channel_infos,
        symbol_visitor.lexical_functions,
        symbol_visitor.bound_call_args,
        symbol_visitor.bound_struct_fields,
        symbol_visitor.callable_call_specialization_map,
        symbol_visitor.operator_calls,
    )
    return codegen.generate()


def compile_zinc(source_path: Path) -> str:
    """Compile a Zinc entry file to Rust."""
    return compile_zinc_program(source_path).render()


# === Non-deterministic test support ===


def is_nondeterministic_test(test_path: str) -> bool:
    """Check if a test should use non-deterministic comparison."""
    parts = Path(test_path).parts
    return NON_DETERMINISTIC_FOLDER in parts


def lines_as_multiset(text: str) -> Counter[str]:
    """Convert text to a multiset (Counter) of lines."""
    return Counter(text.splitlines())


def compare_outputs_as_multisets(expected: str, observed: str) -> bool:
    """Compare two outputs as multisets of lines (ignoring line order)."""
    return lines_as_multiset(expected) == lines_as_multiset(observed)


def format_multiset_diff(expected: str, observed: str) -> str:
    """Format a helpful diff message for multiset comparison failure."""
    expected_multiset = lines_as_multiset(expected)
    observed_multiset = lines_as_multiset(observed)

    missing = expected_multiset - observed_multiset
    extra = observed_multiset - expected_multiset

    lines = []
    if missing:
        lines.append("Missing lines (expected but not found):")
        for line, count in sorted(missing.items()):
            lines.append(f"  {repr(line)} x{count}")
    if extra:
        lines.append("Extra lines (found but not expected):")
        for line, count in sorted(extra.items()):
            lines.append(f"  {repr(line)} x{count}")

    lines.extend(
        ["", f"Expected ({len(expected.splitlines())} lines):", expected, f"Observed ({len(observed.splitlines())} lines):", observed]
    )
    return "\n".join(lines)


def run_cargo_bin(test_path: str) -> str:
    """Run a test binary using cargo and return its output.

    Args:
        test_path: Relative path without extension, e.g., "arithmetic" or "structs/01_basic_fields"
    """
    # Binary name uses underscores for path separators
    bin_name = test_path.replace("/", "_")
    binary_path = RUST_SOURCE_DIR / "target" / "release" / bin_name
    if not binary_path.exists():
        build_result = subprocess.run(
            ["cargo", "build", "--bin", bin_name, "--release"],
            capture_output=True,
            text=True,
            cwd=RUST_SOURCE_DIR,
        )
        if build_result.returncode != 0:
            raise RuntimeError(f"Cargo build failed for {bin_name}:\n{build_result.stderr}")
    with tempfile.NamedTemporaryFile(mode="w+", encoding="utf-8") as stdout_file:
        result = subprocess.run(
            [str(binary_path)],
            stdout=stdout_file,
            stderr=subprocess.PIPE,
            text=True,
            cwd=RUST_SOURCE_DIR,
        )
        stdout_file.seek(0)
        stdout = stdout_file.read()
    if result.returncode != 0:
        raise RuntimeError(f"Cargo run failed for {bin_name}:\n{result.stderr}")
    return stdout


def build_cargo_project() -> None:
    """Build the entire Cargo project once."""
    result = subprocess.run(
        ["cargo", "build", "--release"],
        capture_output=True,
        text=True,
        cwd=RUST_SOURCE_DIR,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Cargo build failed:\n{result.stderr}")


def assert_compile_error_files(group: str) -> None:
    """Compile all negative fixtures in a group and check their expected diagnostics."""
    source_paths = get_compile_error_files(group)
    assert source_paths, f"No compile-error fixtures found for group: {group}"
    for source_path in source_paths:
        expected_error = read_expected_error(source_path)
        try:
            with pytest.raises((ZincTypeError, ZincModuleError), match=expected_error):
                compile_zinc(source_path)
        except AssertionError as exc:
            raise AssertionError(f"{source_path}: {exc}") from exc


@pytest.mark.parametrize("group", COMPILE_ERROR_GROUPS, ids=list(COMPILE_ERROR_GROUPS))
def test_compile_error_group(group: str) -> None:
    """Each negative fixture group fails during package loading or Zinc resolution."""
    assert_compile_error_files(group)


def test_missing_pkg_toml(tmp_path: Path) -> None:
    """A Zinc entry file must live under a package root."""
    entry = tmp_path / "main.zn"
    entry.write_text(
        "\n".join(
            [
                "fn main() {",
                "    print(1)",
                "}",
            ]
        )
    )

    with pytest.raises(ZincModuleError, match=r"missing pkg\.toml"):
        compile_zinc(entry)


def assert_no_inline_runtime_helpers(rust_code: str) -> None:
    """Assert generated Rust references the runtime crate instead of inlining helpers."""
    for definition in INLINE_RUNTIME_DEFINITIONS:
        assert definition not in rust_code


def test_runtime_imports_are_feature_scoped() -> None:
    """Generated Rust imports only the runtime families used by the fixture."""
    arithmetic = compile_zinc_program(ZINC_SOURCE_DIR / "arithmetic.zn")
    arithmetic_code = arithmetic.render()
    assert arithmetic.runtime_features == set()
    assert "zinc_internal" not in arithmetic_code
    assert_no_inline_runtime_helpers(arithmetic_code)

    channel = compile_zinc_program(ZINC_SOURCE_DIR / "concurrency/channels/01_local_round_trip.zn")
    channel_code = channel.render()
    assert channel.runtime_features == {"channel"}
    assert "use zinc_internal::{Channel};" in channel_code
    assert_no_inline_runtime_helpers(channel_code)

    context = compile_zinc_program(ZINC_SOURCE_DIR / "concurrency/select/08_context_done.zn")
    context_code = context.render()
    assert context.runtime_features == {"context"}
    assert "use zinc_internal::{Context};" in context_code
    assert_no_inline_runtime_helpers(context_code)

    metadata = compile_zinc_program(ZINC_SOURCE_DIR / "metadata/03_constraints_and_orders.zn")
    metadata_code = metadata.render()
    assert metadata.runtime_features == {"metadata"}
    assert "TypeMeta" in metadata_code
    assert "use zinc_internal::{" in metadata_code
    assert_no_inline_runtime_helpers(metadata_code)


@pytest.mark.parametrize("test_path", get_test_cases())
def test_compile(test_path: str) -> None:
    """Test that compiling a source file produces the expected output.

    Args:
        test_path: Relative path without extension, e.g., "arithmetic" or "structs/01_basic_fields"
    """
    zinc_file = ZINC_SOURCE_DIR / f"{test_path}.zn"
    rust_file = RUST_SRC_DIR / f"{test_path}.rs"

    assert zinc_file.exists(), f"Source file not found: {zinc_file}"
    assert rust_file.exists(), f"Expected output file not found: {rust_file}"
    rust_code = rust_file.read_text()

    observed_rust_code = compile_zinc(zinc_file)

    assert observed_rust_code == rust_code, (
        f"Compilation output mismatch for {test_path}\nExpected:\n{rust_code}\nObserved:\n{observed_rust_code}"
    )

    # Run the binary using cargo
    output = run_cargo_bin(test_path)
    # Output file path mirrors the test path structure
    expected_output_file = OUTPUT_DIR / f"{test_path}.out"
    expected_output = expected_output_file.read_text()

    if is_nondeterministic_test(test_path):
        assert compare_outputs_as_multisets(expected_output, output), (
            f"Execution output mismatch for {test_path} (non-deterministic comparison)\n{format_multiset_diff(expected_output, output)}"
        )
    else:
        assert output == expected_output, f"Execution output mismatch for {test_path}\nExpected:\n{expected_output}\nObserved:\n{output}"


@click.command()
@click.option(
    "--update-output",
    "update_output",
    help="Update the expected output to match what the system currently does",
    is_flag=True,
    default=False,
)
def main(update_output: bool) -> None:
    """Main entry point for running tests."""
    configure_logging("INFO")
    logger = get_logger()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    RUST_SRC_DIR.mkdir(parents=True, exist_ok=True)

    # Collect all test paths (including subdirectories)
    test_paths: list[str] = []
    runtime_features: set[str] = set()
    for source_file in ZINC_SOURCE_DIR.glob("**/*.zn"):
        # Get path relative to ZINC_SOURCE_DIR, without extension
        relative = source_file.relative_to(ZINC_SOURCE_DIR).with_suffix("")
        test_path = str(relative)
        if relative.parts and relative.parts[0] == COMPILE_ERROR_DIR.name:
            continue
        if not is_entry_fixture(relative):
            continue
        test_paths.append(test_path)

        # read the zinc source file
        # compile it to rust
        program = compile_zinc_program(source_file)
        rust_code = program.render()
        runtime_features.update(program.runtime_features)

        if update_output:
            # Write rust code to cargo src directory (create subdirs as needed)
            output_file = RUST_SRC_DIR / f"{test_path}.rs"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(rust_code)

            logger.info(event="wrote_rust", ctx={"rust": str(output_file)})

    if update_output:
        # Generate Cargo.toml with all test binaries
        cargo_content = generate_cargo_toml(test_paths, runtime_features)
        CARGO_TOML.write_text(cargo_content)
        logger.info(event="wrote_cargo_toml", ctx={"path": str(CARGO_TOML)})

        # Build all binaries once
        logger.info(event="building_cargo")
        build_cargo_project()

        # Run each binary and capture output
        for test_path in test_paths:
            # run the rust binary and capture the output
            output = run_cargo_bin(test_path)

            # write the output to the expected output file (create subdirs as needed)
            expected_output_file = OUTPUT_DIR / f"{test_path}.out"
            expected_output_file.parent.mkdir(parents=True, exist_ok=True)
            expected_output_file.write_text(output)

            logger.info(
                event="updated_test",
                ctx={
                    "zinc": str(ZINC_SOURCE_DIR / f"{test_path}.zn"),
                    "rust": str(RUST_SRC_DIR / f"{test_path}.rs"),
                    "output": str(expected_output_file),
                },
            )


if __name__ == "__main__":
    main()
