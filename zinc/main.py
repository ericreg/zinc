import click
from pathlib import Path
from antlr4 import InputStream, CommonTokenStream

from zinc.parser.zincLexer import zincLexer as ZincLexer
from zinc.parser.zincParser import zincParser as ZincParser
from zinc.visitor import Visitor, Program
from zinc.struct_logging import configure_logging, get_logger

configure_logging()
logger = get_logger()


@click.group()
@click.version_option(version="0.1.0", prog_name="zinc")
def main():
    """Zinc - A language that compiles to Rust."""
    pass


@main.command()
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "-o", "--output", type=click.Path(path_type=Path), help="Output file path"
)
def compile(file: Path, output: Path | None):
    """Compile a Zinc source file to Rust."""
    input_text = file.read_text()

    input_stream = InputStream(input_text)
    lexer = ZincLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = ZincParser(stream)
    tree = parser.program()

    visitor = Visitor()
    visitor.visit(tree)

    program = Program(scope=visitor._scope, statements=visitor.statements)
    rust_code = program.render()

    if output:
        output.write_text(rust_code)
        logger.info(f"Compiled {file} to {output}")
    else:
        click.echo(rust_code)


@main.command()
@click.argument("file", type=click.Path(exists=True, path_type=Path))
def tree(file: Path):
    """Print the AST of a Zinc source file."""
    input_text = file.read_text()

    input_stream = InputStream(input_text)
    lexer = ZincLexer(input_stream)

    stream = CommonTokenStream(lexer)
    parser = ZincParser(stream)

    tree = parser.program()

    visitor = Visitor()
    visitor.visit(tree)

    program = Program(scope=visitor._scope, statements=visitor.statements)
    click.echo(program)


@main.command()
@click.argument("file", type=click.Path(exists=True, path_type=Path))
def check(file: Path):
    """Check a Zinc source file for syntax errors."""
    input_text = file.read_text()

    input_stream = InputStream(input_text)
    lexer = ZincLexer(input_stream)

    stream = CommonTokenStream(lexer)
    parser = ZincParser(stream)

    tree = parser.program()

    if parser.getNumberOfSyntaxErrors() > 0:
        click.echo(
            f"Found {parser.getNumberOfSyntaxErrors()} syntax error(s)", err=True
        )
        raise SystemExit(1)
    else:
        click.echo(f"{file}: OK")


if __name__ == "__main__":
    main()
