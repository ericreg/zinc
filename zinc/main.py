"""Command-line interface for the Zinc compiler."""

import json
from pathlib import Path

import click
from zinc.atlas import AtlasBuilder
from zinc.codegen import CodeGenVisitor
from zinc.modules import build_module_graph
from zinc.struct_logging import configure_logging, get_logger
from zinc.symbols import SymbolTableVisitor

configure_logging()
logger = get_logger()


@click.group()
@click.version_option(version="0.1.0", prog_name="zinc")
def main():
    """Zinc - A language that compiles to Rust."""
    pass


def _compile_pipeline(file: Path):
    """Build the module graph, atlas, symbols, and codegen for a file."""
    module_graph = build_module_graph(file)
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
    )
    return module_graph, atlas, symbols, codegen


@main.command()
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.option("-o", "--output", type=click.Path(path_type=Path), help="Output file path")
def compile(file: Path, output: Path | None):
    """Compile a Zinc source file to Rust."""
    _, _, _, codegen = _compile_pipeline(file)
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
    _, _, _, codegen = _compile_pipeline(file)
    program = codegen.generate()
    click.echo(program)


@main.command()
@click.argument("file", type=click.Path(exists=True, path_type=Path))
def check(file: Path):
    """Check a Zinc source file for syntax errors."""
    _compile_pipeline(file)
    click.echo(f"{file}: OK")


@main.command("resolve-types")
@click.argument("file", type=click.Path(exists=True, path_type=Path))
def resolve_types(file: Path):
    """Run type resolution and print the SymbolTable as JSON."""
    _, _, symbols, _ = _compile_pipeline(file)

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
