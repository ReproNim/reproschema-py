import os
from pathlib import Path

import click

from . import __version__, get_logger, set_logger_level
from .migrate import migrate2newschema
from .redcap2reproschema import redcap2reproschema as redcap2rs
from .reproschema2redcap import reproschema2redcap as rs2redcap

lgr = get_logger()


def print_version(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    click.echo(__version__)
    ctx.exit()


# group to provide commands
@click.group()
@click.option(
    "--version",
    is_flag=True,
    callback=print_version,
    expose_value=False,
    is_eager=True,
)
@click.option(
    "-l",
    "--log-level",
    help="Log level name",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
    default="INFO",
    show_default=True,
)
def main(log_level):
    """A client to support interactions with ReproSchema

    To see help for a specific command, run

    reproschema COMMAND --help
        e.g. reproschema validate --help
    """
    set_logger_level(get_logger(), log_level)


@main.command()
@click.argument("path", nargs=1, type=str)
def validate(path):
    """
    Validates if the path has a valid reproschema format
    """
    if not (path.startswith("http") or os.path.exists(path)):
        raise ValueError(
            f"{path} must be a URL or an existing file or directory"
        )
    from .validate import validate

    result = validate(path)
    if result:
        click.echo("Validation successful")


@main.command()
@click.argument("path", nargs=1, type=click.Path(exists=True, dir_okay=True))
@click.option("--inplace", is_flag=True, help="Changing file in place")
@click.option(
    "--fixed-path",
    type=click.Path(dir_okay=True, writable=True, resolve_path=True),
    help="Path to the fixed file/directory, if not provide suffix 'after_migration' is used",
)
def migrate(path, inplace, fixed_path):
    """
    Updates to a new reproschema version
    """
    if not (path.startswith("http") or os.path.exists(path)):
        raise ValueError(
            f"{path} must be a URL or an existing file or directory"
        )
    if fixed_path and inplace:
        raise Exception("Either inplace or fixed_path has to be provided.")
    new_path = migrate2newschema(path, inplace=inplace, fixed_path=fixed_path)
    if new_path:
        click.echo(f"File/Directory after migration {new_path}")


@main.command()
@click.option(
    "--format",
    help="Output format",
    type=click.Choice(["jsonld", "n-triples", "turtle"]),
    default="n-triples",
    show_default=True,
)
@click.option(
    "--prefixfile", default=None, type=click.Path(exists=True, dir_okay=False)
)
@click.option(
    "--contextfile", default=None, type=click.Path(exists=True, dir_okay=False)
)
@click.argument("path", nargs=1, type=str)
def convert(path, format, prefixfile, contextfile):
    """
    Converts a path to a different format, jsonld, n-triples or turtle
    """
    if not (path.startswith("http") or os.path.exists(path)):
        raise ValueError(
            f"{path} must be a URL or an existing file or directory"
        )
    from .jsonldutils import to_newformat

    print(to_newformat(path, format, prefixfile, contextfile))


@main.command()
@click.option(
    "--format",
    help="Input format",
    type=click.Choice(["csv"]),
    default="csv",
    show_default=True,
)
@click.argument("path", nargs=1, type=str)
def create(path, format):
    if not (path.startswith("http") or os.path.exists(path)):
        raise ValueError(
            f"{path} must be a URL or an existing file or directory"
        )
    raise NotImplementedError


@main.command()
@click.option(
    "--port",
    help="Port to serve on",
    type=int,
    default=8000,
    show_default=True,
)
def serve(port):
    from .utils import start_server

    start_server(port=port)


@main.command()
@click.argument("csv_path", type=click.Path(exists=True, dir_okay=False))
@click.argument("yaml_path", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--output-path",
    type=click.Path(dir_okay=True, writable=True, resolve_path=True),
    default=".",
    show_default=True,
    help="Path to the output directory, defaults to the current directory.",
)
def redcap2reproschema(csv_path, yaml_path, output_path):
    """
    Converts REDCap CSV files to Reproschema format.
    """
    try:
        redcap2rs(csv_path, yaml_path, output_path)
        click.echo("Converted REDCap data dictionary to Reproschema format.")
    except Exception as e:
        raise click.ClickException(f"Error during conversion: {e}")


@main.command()
@click.argument("input_path", type=click.Path(exists=True, dir_okay=True))
@click.argument("output_csv_path", type=click.Path(writable=True))
def reproschema2redcap(input_path, output_csv_path):
    """
    Converts reproschema protocol to REDCap CSV format.
    """
    # Convert input_path to a Path object
    input_path_obj = Path(input_path)
    rs2redcap(input_path_obj, output_csv_path)
    click.echo(
        f"Converted reproschema protocol from {input_path} to Redcap CSV at {output_csv_path}"
    )
