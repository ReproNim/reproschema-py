import json
import os
from pathlib import Path

from .jsonldutils import load_file, validate_data
from .utils import lgr, start_server, stop_server


def validate_dir(directory, started=False, http_kwargs={}):
    """Validate a directory containing JSONLD documents against the ReproSchema pydantic model.

    Parameters
    ----------
    directory: str
        Path to directory to walk for validation
    started : bool
        Whether an http server exists or not
    http_kwargs : dict
        Keyword arguments for the http server. Valid keywords are: port, path
        and tmpdir

    Returns
    -------
    conforms: bool
        Whether the document is conformant with the shape. Raises an exception
        if any document is non-conformant.

    """
    if not os.path.isdir(directory):
        raise Exception(f"{directory} is not a directory")
    print(f"Validating directory {directory}")
    stop = None
    if not started:
        stop, port = start_server(**http_kwargs)
        http_kwargs["port"] = port
    else:
        if "port" not in http_kwargs:
            raise KeyError("HTTP server started, but port key is missing")

    for root, _, files in os.walk(directory):
        for name in files:
            full_file_name = os.path.join(root, name)

            if Path(full_file_name).suffix not in [
                ".jsonld",
                "json",
                "js",
                "",
            ]:
                lgr.info(f"Skipping file {full_file_name}")
                continue

            lgr.debug(f"Validating file {full_file_name}")
            try:
                data = load_file(
                    full_file_name, started=True, http_kwargs=http_kwargs
                )
                if len(data) == 0:
                    raise ValueError("Empty data graph")
                print(f"Validating {full_file_name}")
                conforms, vtext = validate_data(data)
            except (ValueError, json.JSONDecodeError):
                if stop is not None:
                    stop_server(stop)
                raise
            else:
                if not conforms:
                    lgr.critical(
                        f"File {full_file_name} has validation errors."
                    )
                    if stop is not None:
                        stop_server(stop)
                    raise ValueError(vtext)
    if not started:
        stop_server(stop)
    return True


def validate(path):
    """Helper function to validate directory or path

    Parameters
    ----------
    path : path-like
        Path to folder or file containing JSONLD documents.

    Returns
    -------
    conforms : bool
        Returns true if the folder or file conforms else raises ValueError
        exception.

    """
    if os.path.isdir(path):
        conforms = validate_dir(path)
    else:
        # Skip validation for .DS_Store files
        if Path(path).name == ".DS_Store":
            lgr.info(f"{path} is a .DS_Store file and is skipped.")
            return True
        data = load_file(path, started=False)
        conforms, vtext = validate_data(data)
        if not conforms:
            lgr.critical(f"File {path} has validation errors.")
            raise ValueError(vtext)
    lgr.info(f"{path} conforms.")
    return conforms
