"""Parameterized tests for Zinc compilation."""

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
OUTPUT_DIR = TEST_DIR / "output"


def get_test_cases() -> list[str]:
    """Discover test cases by finding .zinc files in source directory."""
    if not ZINC_SOURCE_DIR.exists():
        return []
    return [f.stem for f in ZINC_SOURCE_DIR.glob("*.zinc")]


def compile_zinc(source_code: str) -> str:
    """Compile Zinc source code to Rust."""
    input_stream = InputStream(source_code)
    lexer = ZincLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = ZincParser(stream)
    tree = parser.program()

    visitor = Visitor()
    visitor.visit(tree)

    program = Program(scope=visitor._scope, statements=visitor.statements)
    return program.render()


@pytest.mark.parametrize("test_name", get_test_cases())
def test_compile(test_name: str) -> None:
    """Test that compiling a source file produces the expected output."""
    zinc_file = ZINC_SOURCE_DIR / f"{test_name}.zinc"
    rust_file = RUST_SOURCE_DIR / f"{test_name}.rs"

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

    # compile the rust code 
    binary_path = compile_rust(rust_file)

    # execute
    output = execute_binary(binary_path)
    expected_output_file = OUTPUT_DIR / f"{test_name}.out"
    expected_output = expected_output_file.read_text()
    assert output == expected_output, (
        f"Execution output mismatch for {test_name}\n"
        f"Expected:\n{expected_output}\n"
        f"Observed:\n{output}"
    )

    # clean up
    binary_path.unlink()



def compile_rust(file_path: Path) -> Path:
    """Compile the Rust code at the given file path using rustc.

    Returns the path to the compiled binary.
    """
    import subprocess

    binary_path = file_path.parent / file_path.stem
    result = subprocess.run(
        ["rustc", str(file_path), "-o", str(binary_path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Rust compilation failed for {file_path}:\n{result.stderr}"
        )
    return binary_path


def execute_binary(binary_path: Path) -> str:
    """Execute a compiled binary and return its output."""
    import subprocess

    result = subprocess.run(
        [str(binary_path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Binary execution failed for {binary_path}:\n{result.stderr}"
        )
    return result.stdout

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
    for source_file in ZINC_SOURCE_DIR.glob("*.zinc"):

        # read the zinc source file
        zinc_code = source_file.read_text()

        # compile it to rust
        rust_code = compile_zinc(zinc_code)

        if update_output:
            output_file = RUST_SOURCE_DIR / f"{source_file.stem}.rs"
            output_file.write_text(rust_code)

            # compile the rust code to the output file
            rust_binary = compile_rust(output_file)

            # run the rust binary and capture the output
            output = execute_binary(rust_binary)

            # write the output to the expected output file
            expected_output_file = OUTPUT_DIR / f"{source_file.stem}.out"
            expected_output_file.write_text(output)

            # delete the rust binary
            rust_binary.unlink()

            logger.info(event="updated_test", ctx={ "zinc": str(source_file), "rust": str(output_file), "output": str(expected_output_file) })
        


if __name__ == "__main__":
    main()

