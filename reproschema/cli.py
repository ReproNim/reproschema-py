import json
import os
import shutil
from collections import OrderedDict
from pathlib import Path

import click
import pandas as pd
from fhir.resources.questionnaire import Questionnaire

from . import __version__, get_logger, set_logger_level
from .migrate import migrate2newschema
from .output2redcap import parse_survey
from .redcap2reproschema import redcap2reproschema as redcap2rs
from .reproschema2fhir import convert_to_fhir
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


@main.command()
@click.argument("survey_file", type=str)
@click.argument("redcap_csv", type=str)
def output2redcap(survey_file, redcap_csv):
    """
    Generates redcap csv given the audio and survey data from reproschema ui

    survey_file is the location of the surveys generated from reproschema ui
    redcap_csv is the path to store the newly generated redcap csv

    """
    merged_questionnaire_data = []
    # load each file recursively within the folder into its own key
    content = OrderedDict()
    for file in Path(survey_file).rglob("*"):
        if file.is_file():
            filename = str(file.relative_to(survey_file))
            with open(f"{survey_file}/{filename}", "r") as f:
                content[filename] = json.load(f)

    for questionnaire in content.keys():  # activity files
        try:
            record_id = (survey_file.split("/")[-1]).split()[0]
            survey_data = content[questionnaire]
            merged_questionnaire_data += parse_survey(
                survey_data, record_id, questionnaire
            )
        except Exception:
            continue

    survey_df = pd.concat(merged_questionnaire_data, ignore_index=True)
    Path(redcap_csv).mkdir(parents=True, exist_ok=True)

    merged_csv_path = os.path.join(redcap_csv, "redcap.csv")
    survey_df.to_csv(merged_csv_path, index=False)
    click.echo(
        f"Converted reproschema-ui output from {survey_file} to Redcap CSV at {redcap_csv}"
    )


@main.command()
@click.argument("reproschema_questionnaire", type=str)
@click.argument("output", type=str)
def reproschema2fhir(reproschema_questionnaire, output):
    """
    Generates FHIR questionnaire resources from reproschema activities

    reproschema_questionnaire is the location of all reproschema activities
    output is the path to store the newly generated fhir json
    """
    output_path = Path(output)
    reproschema_folders = Path(reproschema_questionnaire)
    if not os.path.isdir(reproschema_folders):
        raise FileNotFoundError(
            f"{reproschema_folders} does not exist. Please check if folder exists and is located at the correct directory"
        )
    reproschema_folders = [
        Path(f) for f in reproschema_folders.iterdir() if f.is_dir()
    ]
    for reproschema_folder in reproschema_folders:
        # load each file recursively within the folder into its own key in the reproschema_content dict
        reproschema_content = OrderedDict()
        for file in reproschema_folder.glob("**/*"):
            if file.is_file():
                # get the full path to the file *after* the base reproschema_folder path
                # since files can be referenced by relative paths, we need to keep track of relative location
                filename = str(file.relative_to(reproschema_folder))
                with open(f"{reproschema_folder}/{filename}") as f:
                    reproschema_content[filename] = json.loads(f.read())

        schema_name = [
            name
            for name in (reproschema_content.keys())
            if name.endswith("_schema")
        ][0]
        reproschema_schema = reproschema_content[schema_name]

        if (
            (
                "schema:version" in reproschema_schema
                and reproschema_schema["schema:version"]
                not in ("0.0.1", "1.0.0-rc1", "1.0.0")
            )
            or "schemaVersion" in reproschema_schema
            and reproschema_schema["schemaVersion"]
            not in ("0.0.1", "1.0.0-rc1", "1.0.0-rc4", "1.0.0")
        ):
            raise ValueError(
                "Unable to work with reproschema versions other than 0.0.1, 1.0.0-rc1, and 1.0.0-rc4"
            )

        fhir_questionnaire = convert_to_fhir(reproschema_content)

        # validate the json using fhir resources
        try:
            Questionnaire.model_validate(fhir_questionnaire)
        except Exception:
            raise Exception("Fhir Questionnaire is not valid")

        # get filename from the reproschema_folder name provided

        file_name = reproschema_folder.parts[-1]

        dirpath = Path(output_path / file_name)
        if dirpath.exists() and dirpath.is_dir():
            shutil.rmtree(dirpath)

        paths = [output_path / file_name]

        for folder in paths:
            folder.mkdir(parents=True, exist_ok=True)

        with open(output_path / f"{file_name}/{file_name}.json", "w+") as f:
            f.write(json.dumps(fhir_questionnaire))
