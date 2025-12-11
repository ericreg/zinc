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


def get_test_cases() -> list[str]:
    """Discover test cases by finding .zn files in source directory."""
    if not ZINC_SOURCE_DIR.exists():
        return []
    return [f.stem for f in ZINC_SOURCE_DIR.glob("*.zn")]


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


def run_cargo_bin(test_name: str) -> str:
    """Run a test binary using cargo and return its output."""
    result = subprocess.run(
        ["cargo", "run", "--bin", test_name, "-q", "--release"],
        capture_output=True,
        text=True,
        cwd=RUST_SOURCE_DIR,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Cargo run failed for {test_name}:\n{result.stderr}"
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


@pytest.mark.parametrize("test_name", get_test_cases())
def test_compile(test_name: str) -> None:
    """Test that compiling a source file produces the expected output."""
    zinc_file = ZINC_SOURCE_DIR / f"{test_name}.zn"
    rust_file = RUST_SRC_DIR / f"{test_name}.rs"

    assert zinc_file.exists(), f"Source file not found: {zinc_file}"
    assert rust_file.exists(), f"Expected output file not found: {rust_file}"
    zinc_code = zinc_file.read_text()
    rust_code = rust_file.read_text()

    observed_rust_code = compile_zinc(zinc_code)

    assert observed_rust_code == rust_code, (
        f"Compilation output mismatch for {test_name}\n"
        f"Expected:\n{rust_code}\n"
        f"Observed:\n{observed_rust_code}"
    )

    # Run the binary using cargo
    output = run_cargo_bin(test_name)
    expected_output_file = OUTPUT_DIR / f"{test_name}.out"
    expected_output = expected_output_file.read_text()
    assert output == expected_output, (
        f"Execution output mismatch for {test_name}\n"
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

    for source_file in ZINC_SOURCE_DIR.glob("*.zn"):
        test_name = source_file.stem

        # read the zinc source file
        zinc_code = source_file.read_text()

        # compile it to rust
        rust_code = compile_zinc(zinc_code)

        if update_output:
            # Write rust code to cargo src directory
            output_file = RUST_SRC_DIR / f"{test_name}.rs"
            output_file.write_text(rust_code)

            logger.info(event="wrote_rust", ctx={"rust": str(output_file)})

    if update_output:
        # Build all binaries once
        logger.info(event="building_cargo")
        build_cargo_project()

        # Run each binary and capture output
        for source_file in ZINC_SOURCE_DIR.glob("*.zn"):
            test_name = source_file.stem

            # run the rust binary and capture the output
            output = run_cargo_bin(test_name)

            # write the output to the expected output file
            expected_output_file = OUTPUT_DIR / f"{test_name}.out"
            expected_output_file.write_text(output)

            logger.info(
                event="updated_test",
                ctx={
                    "zinc": str(source_file),
                    "rust": str(RUST_SRC_DIR / f"{test_name}.rs"),
                    "output": str(expected_output_file),
                },
            )


if __name__ == "__main__":
    main()
