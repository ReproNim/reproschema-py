import click

from . import get_logger, set_logger_level
from . import __version__

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
def main(log_level, pdb=False):
    """A client to support interactions with ReproSchema

    To see help for a specific command, run

    reproschema COMMAND --help
        e.g. reproschema validate --help
    """
    set_logger_level(get_logger(), log_level)


@main.command()
@click.option("--shapedir", default=None, type=click.Path(exists=True, dir_okay=True))
@click.argument("path", nargs=1, type=click.Path(exists=True, dir_okay=True))
def validate(shapedir, path):
    from .validate import validate

    validate(shapedir, path)


@main.command()
@click.option(
    "--format",
    help="Output format",
    type=click.Choice(["n-triples", "turtle"]),
    default="n-triples",
    show_default=True,
)
@click.argument("path", nargs=1, type=click.Path(exists=True, dir_okay=False))
def convert(path, format):
    from .jsonldutils import to_nt

    print(to_nt(path, format))


@main.command()
@click.option(
    "--format",
    help="Input format",
    type=click.Choice(["csv"]),
    default="csv",
    show_default=True,
)
@click.argument("path", nargs=1, type=click.Path(exists=True, dir_okay=False))
def create(path, format):
    raise NotImplementedError


@main.command()
@click.option(
    "--port", help="Port to serve on", type=int, default=8000, show_default=True
)
def serve(port):
    from .utils import start_server

    start_server(port=port)
