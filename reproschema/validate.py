import json
from pathlib import Path

from .jsonldutils import load_file, validate_data
from .utils import lgr, start_server, stop_server

DIR_TO_SKIP = [
    ".git",
    ".github",
    "__pycache__",
    "env",
    "venv",
]
FILES_TO_SKIP = [
    ".DS_Store",
    ".gitignore",
    ".flake8",
    ".autorc",
    "LICENSE",
    "Makefile",
]
SUPPORTED_EXTENSIONS = [
    ".jsonld",
    "json",
    "js",
    "",
]


def validate_dir(
    directory: str,
    started: bool = False,
    http_kwargs: None | dict[str, int] = None,
    stop=None,
):
    """Validate a directory containing JSONLD documents against the ReproSchema pydantic model.

    Recursively goes through the directory tree and validates files with the allowed extensions.

    Parameters
    ----------
    directory: str
        Path to directory to walk for validation

    started : bool
        Whether an http server exists or not

    http_kwargs : dict or None
        Keyword arguments for the http server. Valid keywords are: port, path
        and tmpdir

    stop: None or function
        Function to use to stop the HTTP server

    Returns
    -------
    conforms: bool
        Whether the document is conformant with the shape. Raises an exception
        if any document is non-conformant.

    """
    if http_kwargs is None:
        http_kwargs = {}

    directory = Path(directory)

    if not directory.is_dir():
        if stop is not None:
            stop_server(stop)
        raise Exception(f"{str(directory)} is not a directory")

    if directory.name in DIR_TO_SKIP:
        lgr.info(f"Skipping directory {directory}")
        return True

    lgr.info(f"Validating directory {directory}")

    files_to_validate = [
        str(x)
        for x in directory.iterdir()
        if x.is_file()
        and x.name not in FILES_TO_SKIP
        and x.suffix in SUPPORTED_EXTENSIONS
    ]

    for name in files_to_validate:
        lgr.debug(f"Validating file {name}")

        try:
            data = load_file(name, started=started, http_kwargs=http_kwargs)
            if len(data) == 0:
                if stop is not None:
                    stop_server(stop)
                raise ValueError(f"Empty data graph in file {name}")
            conforms, vtext = validate_data(data, schemaname=Path(name).name)
        except (ValueError, json.JSONDecodeError):
            if stop is not None:
                stop_server(stop)
            raise
        else:
            if not conforms:
                lgr.critical(f"File {name} has validation errors.")
                stop_server(stop)
                raise ValueError(vtext)

    dirs_to_validate = [
        str(x)
        for x in directory.iterdir()
        if x.is_dir() and x.name not in DIR_TO_SKIP
    ]

    for dir in dirs_to_validate:
        conforms, stop = validate_dir(
            dir, started=started, http_kwargs=http_kwargs, stop=stop
        )

    return True, stop


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
    if Path(path).is_dir():
        lgr.info(f"Validating directory {path}")
        stop, port = start_server()
        http_kwargs = {"port": port}
        started = True
        conforms, _ = validate_dir(
            path, started=started, http_kwargs=http_kwargs, stop=stop
        )
        stop_server(stop)
    else:
        if Path(path).name in FILES_TO_SKIP:
            lgr.info(f"Skipping file {path}")
            return True
        data = load_file(path, started=False)
        conforms, vtext = validate_data(data, schemaname=Path(path).name)
        if not conforms:
            lgr.critical(f"File {path} has validation errors.")
            raise ValueError(vtext)

    lgr.info(f"{path} conforms.")

    return conforms
