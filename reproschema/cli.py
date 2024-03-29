import os
import click
from pathlib import Path

from . import get_logger, set_logger_level
from . import __version__
from .redcap2reproschema import redcap2reproschema as redcap2rs
from .reproschema2redcap import main as rs2redcap

lgr = get_logger()


def print_version(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    click.echo(__version__)
    ctx.exit()


# group to provide commands
@click.group()
@click.option(
    "--version", is_flag=True, callback=print_version, expose_value=False, is_eager=True
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
@click.option("--shapefile", default=None, type=click.Path(exists=True, dir_okay=False))
@click.argument("path", nargs=1, type=str)
def validate(shapefile, path):
    if not (path.startswith("http") or os.path.exists(path)):
        raise ValueError(f"{path} must be a URL or an existing file or directory")
    from .validate import validate

    validate(shapefile, path)


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
    if not (path.startswith("http") or os.path.exists(path)):
        raise ValueError(f"{path} must be a URL or an existing file or directory")
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
        raise ValueError(f"{path} must be a URL or an existing file or directory")
    raise NotImplementedError


@main.command()
@click.option(
    "--port", help="Port to serve on", type=int, default=8000, show_default=True
)
def serve(port):
    from .utils import start_server

    start_server(port=port)


@main.command()
@click.argument("csv_path", type=click.Path(exists=True, dir_okay=False))
@click.argument("yaml_path", type=click.Path(exists=True, dir_okay=False))
def redcap2reproschema(csv_path, yaml_path):
    """
    Convert REDCap CSV files to Reproschema format.
    """
    try:
        redcap2rs(csv_path, yaml_path)
        click.echo("Converted REDCap data dictionary to Reproschema format.")
    except Exception as e:
        raise click.ClickException(f"Error during conversion: {e}")


@main.command()
@click.argument("input_path", type=click.Path(exists=True, dir_okay=True))
@click.argument("output_csv_path", type=click.Path(writable=True))
def reproschema2redcap(input_path, output_csv_path):
    """
    Convert reproschema protocol to REDCap CSV format.
    """
    # Convert input_path to a Path object
    input_path_obj = Path(input_path)
    rs2redcap(input_path_obj, output_csv_path)
    click.echo(
        f"Converted reproschema protocol from {input_path} to Redcap CSV at {output_csv_path}"
    )
