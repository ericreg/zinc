"""Parameterized tests for Zinc compilation."""

import subprocess
from pathlib import Path

import click
import pytest
from antlr4 import CommonTokenStream, InputStream

from zinc.parser.zincLexer import zincLexer as ZincLexer
from zinc.parser.zincParser import zincParser as ZincParser
from zinc.struct_logging import configure_logging, get_logger
from zinc.visitor import Program, Visitor

TEST_DIR = Path(__file__).parent
ZINC_SOURCE_DIR = TEST_DIR / "zinc_source"
RUST_SOURCE_DIR = TEST_DIR / "rust_source"
RUST_SRC_DIR = RUST_SOURCE_DIR / "src"  # Cargo src directory
OUTPUT_DIR = TEST_DIR / "output"
CARGO_TOML = RUST_SOURCE_DIR / "Cargo.toml"


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
        test_cases.append(str(relative))
    return test_cases


def generate_cargo_toml(test_paths: list[str]) -> str:
    """Generate Cargo.toml content with binary entries for each test.

    Args:
        test_paths: Relative paths without extension, e.g., "arithmetic" or "structs/01_basic_fields"
    """
    lines = [
        '[package]',
        'name = "zinc_tests"',
        'version = "0.1.0"',
        'edition = "2021"',
        '',
        '[dependencies]',
        'tokio = { version = "1", features = ["full"] }',
        '',
    ]

    for test_path in sorted(test_paths):
        # Binary name uses underscores for path separators (e.g., "structs_01_basic_fields")
        bin_name = test_path.replace("/", "_")
        lines.extend([
            '[[bin]]',
            f'name = "{bin_name}"',
            f'path = "src/{test_path}.rs"',
            '',
        ])

    # Add run_all binary for main.rs if it exists
    if (RUST_SRC_DIR / "main.rs").exists():
        lines.extend([
            '[[bin]]',
            'name = "run_all"',
            'path = "src/main.rs"',
            '',
        ])

    return '\n'.join(lines)


def compile_zinc(source_code: str) -> str:
    """Compile Zinc source code to Rust."""
    input_stream = InputStream(source_code)
    lexer = ZincLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = ZincParser(stream)
    tree = parser.program()

    visitor = Visitor()
    visitor.visit(tree)
    visitor.finalize()  # Pass 2: process assignments
    visitor.monomorphize()  # Pass 3: generate specialized functions

    program = Program(
        scope=visitor._scope,
        statements=visitor.statements,
        monomorphized=visitor._monomorphized,
        uses_spawn=visitor._uses_spawn,
    )
    return program.render()


def run_cargo_bin(test_path: str) -> str:
    """Run a test binary using cargo and return its output.

    Args:
        test_path: Relative path without extension, e.g., "arithmetic" or "structs/01_basic_fields"
    """
    # Binary name uses underscores for path separators
    bin_name = test_path.replace("/", "_")
    result = subprocess.run(
        ["cargo", "run", "--bin", bin_name, "-q", "--release"],
        capture_output=True,
        text=True,
        cwd=RUST_SOURCE_DIR,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Cargo run failed for {bin_name}:\n{result.stderr}"
        )
    return result.stdout


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
    zinc_code = zinc_file.read_text()
    rust_code = rust_file.read_text()

    observed_rust_code = compile_zinc(zinc_code)

    assert observed_rust_code == rust_code, (
        f"Compilation output mismatch for {test_path}\n"
        f"Expected:\n{rust_code}\n"
        f"Observed:\n{observed_rust_code}"
    )

    # Run the binary using cargo
    output = run_cargo_bin(test_path)
    # Output file path mirrors the test path structure
    expected_output_file = OUTPUT_DIR / f"{test_path}.out"
    expected_output = expected_output_file.read_text()
    assert output == expected_output, (
        f"Execution output mismatch for {test_path}\n"
        f"Expected:\n{expected_output}\n"
        f"Observed:\n{output}"
    )


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
    for source_file in ZINC_SOURCE_DIR.glob("**/*.zn"):
        # Get path relative to ZINC_SOURCE_DIR, without extension
        relative = source_file.relative_to(ZINC_SOURCE_DIR).with_suffix("")
        test_path = str(relative)
        test_paths.append(test_path)

        # read the zinc source file
        zinc_code = source_file.read_text()

        # compile it to rust
        rust_code = compile_zinc(zinc_code)

        if update_output:
            # Write rust code to cargo src directory (create subdirs as needed)
            output_file = RUST_SRC_DIR / f"{test_path}.rs"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(rust_code)

            logger.info(event="wrote_rust", ctx={"rust": str(output_file)})

    if update_output:
        # Generate Cargo.toml with all test binaries
        cargo_content = generate_cargo_toml(test_paths)
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
