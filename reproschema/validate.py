import os
from .utils import start_server, stop_server, lgr
from .jsonldutils import load_file, validate_data


def validate_dir(directory, shape_file, started=False, http_kwargs={}):
    """Validate a directory containing JSONLD documents

    .. warning:: This assumes every file in the directory can be read by a json parser.

    Parameters
    ----------
    directory: str
        Path to directory to walk for validation
    shape_file: str
        Path containing validation SHACL shape files
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
    stop = None
    if not started:
        stop, port = start_server(**http_kwargs)
        http_kwargs["port"] = port
    else:
        if "port" not in http_kwargs:
            raise KeyError(f"HTTP server started, but port key is missing")
    for root, dirs, files in os.walk(directory):
        for name in files:
            full_file_name = os.path.join(root, name)
            try:
                data = load_file(full_file_name, started=True, http_kwargs=http_kwargs)
                if len(data) == 0:
                    raise ValueError("Empty data graph")
                conforms, vtext = validate_data(data, shape_file)
            except (ValueError,):
                if stop is not None:
                    stop_server(stop)
                raise
            else:
                if not conforms:
                    lgr.critical(f"File {full_file_name} has validation errors.")
                    if stop is not None:
                        stop_server(stop)
                    raise ValueError(vtext)
    if not started:
        stop_server(stop)
    return True


def validate(shapefile, path):
    """Helper function to validate directory or path

    Parameters
    ----------
    shapefile : path-like
        Path to folder or file containing ReproSchema SHACL descriptors
    path : path-like
        Path to folder or file containing JSONLD documents.

    Returns
    -------
    conforms : bool
        Returns true if the folder or file conforms else raises ValueError
        exception.

    """
    if shapefile is None:
        shapefile = os.path.join(
            os.path.dirname(__file__), "tests", "reproschema-shacl.ttl"
        )
    if os.path.isdir(path):
        conforms = validate_dir(path, shapefile)
    else:
        data = load_file(path, started=False)
        conforms, vtext = validate_data(data, shapefile)
        if not conforms:
            lgr.critical(f"File {path} has validation errors.")
            raise ValueError(vtext)
    lgr.info(f"{path} conforms.")
    return conforms
