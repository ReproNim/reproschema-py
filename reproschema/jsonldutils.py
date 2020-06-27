from pyld import jsonld
import json
import os
from .utils import start_server, stop_server
import requests


def file2shape(filename, shape_dir):
    with open(filename) as json_file:
        data = json.load(json_file)
        if "@type" not in data:
            raise ValueError(f"{filename} missing @type")
        if "Protocol" in data["@type"]:
            shape_file_path = os.path.join(shape_dir, "ProtocolShape.ttl")
        elif "Activity" in data["@type"]:
            shape_file_path = os.path.join(shape_dir, "ActivityShape.ttl")
        elif "Field" in data["@type"]:
            shape_file_path = os.path.join(shape_dir, "FieldShape.ttl")
        elif "ResponseOptions" in data["@type"]:
            shape_file_path = os.path.join(shape_dir, "ResponseOptionsShape.ttl")
    return data, shape_file_path


def localnormalize(data, root=None, started=False, http_kwargs={}):
    """Normalize a JSONLD document using a local HTTP server

    Since PyLD requires an http url, a local server is started to serve the
    document.

    Parameters
    ----------
    data : dict
        Python dictionary containing JSONLD object
    root : str
        Server path to the document such that relative links hold
    started : bool
        Whether an http server exists or not
    http_kwargs : dict
        Keyword arguments for the http server. Valid keywords are: port, path
        and tmpdir

    Returns
    -------
    normalized : str
        A normalized document

    """
    kwargs = {"algorithm": "URDNA2015", "format": "application/n-quads"}
    if root is not None:
        if not started:
            stop = start_server(**http_kwargs)
        base_url = f"http://localhost:8000/{root}/"
        kwargs["base"] = base_url
    normalized = jsonld.normalize(data, kwargs)
    if root is not None:
        if not started:
            stop_server(stop)
    return normalized


def to_nt(path, format):
    """Convert a JSONLD document to n-triples format

    Since PyLD requires an http url, a local server is started to serve the
    document.

    Parameters
    ----------
    path : str
        A local path or remote url to convert to n-triples
    format: str of enum
        Returned format n-triples, turtle

    Returns
    -------
    normalized : str
        A normalized document

    """
    if path.startswith("http"):
        data = requests.get(path).json()
        root = None
    else:
        with open(path) as fp:
            data = json.load(fp)
        root = os.path.dirname(path)
    try:
        nt = localnormalize(data)
    except jsonld.JsonLdError as e:
        if 'only "http" and "https"' in str(e.cause):
            nt = localnormalize(data, root)
    if format == "n-triples":
        return nt
    import rdflib as rl

    g = rl.Graph()
    g.parse(data=nt, format="nt")
    return g.serialize(format=format).decode()
