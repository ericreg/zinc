import json
import click
from pathlib import Path
from antlr4 import InputStream, CommonTokenStream

from zinc.parser.zincLexer import zincLexer as ZincLexer
from zinc.parser.zincParser import zincParser as ZincParser
from zinc.struct_logging import configure_logging, get_logger
from zinc.atlas import AtlasBuilder
from zinc.symbols import SymbolTableVisitor
from zinc.codegen import CodeGenVisitor

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

    # Pass 1: Build Atlas (reachability)
    atlas_builder = AtlasBuilder()
    atlas_builder.visit(tree)
    atlas = atlas_builder.build()

    # Pass 2: Build SymbolTable
    symbol_visitor = SymbolTableVisitor(atlas)
    symbols = symbol_visitor.resolve()

    # Pass 3: Generate Rust code
    codegen = CodeGenVisitor(
        atlas, symbols, symbol_visitor.specialization_map, symbol_visitor._channel_infos
    )
    program = codegen.generate()
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

    # Pass 1: Build Atlas (reachability)
    atlas_builder = AtlasBuilder()
    atlas_builder.visit(tree)
    atlas = atlas_builder.build()

    # Pass 2: Build SymbolTable
    symbol_visitor = SymbolTableVisitor(atlas)
    symbols = symbol_visitor.resolve()

    # Pass 3: Generate Rust code
    codegen = CodeGenVisitor(
        atlas, symbols, symbol_visitor.specialization_map, symbol_visitor._channel_infos
    )
    program = codegen.generate()
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


@main.command("resolve-types")
@click.argument("file", type=click.Path(exists=True, path_type=Path))
def resolve_types(file: Path):
    """Run type resolution and print the SymbolTable as JSON."""
    input_text = file.read_text()

    input_stream = InputStream(input_text)
    lexer = ZincLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = ZincParser(stream)
    tree = parser.program()

    # Pass 1: Build Atlas (reachability)
    atlas_builder = AtlasBuilder()
    atlas_builder.visit(tree)
    atlas = atlas_builder.build()

    # Pass 2: Build SymbolTable
    symbol_visitor = SymbolTableVisitor(atlas)
    symbols = symbol_visitor.resolve()

    # Output as JSON
    output = {
        "symbols": [
            {
                "id": s.id,
                "unique_name": s.unique_name,
                "kind": s.kind.name,
                "type": s.resolved_type.name,
                "interval": f"({s.source_interval[0]}, {s.source_interval[1]})",
            }
            for s in symbols.all_symbols()
        ]
    }
    click.echo(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
