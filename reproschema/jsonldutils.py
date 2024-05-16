from pyld import jsonld
import json
import os
from pathlib import Path
from copy import deepcopy
from urllib.parse import urlparse
from .utils import start_server, stop_server, lgr, fixing_old_schema
from .models import Item, Activity, Protocol, ResponseOption, ResponseActivity, Response


def _is_url(path):
    """
    Determine whether the given path is a URL.
    """
    parsed = urlparse(path)
    return parsed.scheme in ("http", "https", "ftp", "ftps")


def _is_file(path):
    """
    Determine whether the given path is a valid file path.
    """
    return os.path.isfile(path)


def load_file(path_or_url, started=False, http_kwargs={}):
    """Load a file or URL and return the expanded JSON-LD data."""
    path_or_url = str(path_or_url)
    if _is_url(path_or_url):
        data = jsonld.expand(path_or_url)
        if len(data) == 1:
            if "@id" not in data[0] and "id" not in data[0]:
                data[0]["@id"] = path_or_url
    elif _is_file(path_or_url):
        lgr.debug("Reloading with local server")
        root = os.path.dirname(path_or_url)
        if not started:
            stop, port = start_server(**http_kwargs)
        else:
            if "port" not in http_kwargs:
                raise KeyError("port key missing in http_kwargs")
            port = http_kwargs["port"]
        base_url = f"http://localhost:{port}/"
        if root:
            base_url += f"{root}/"
        with open(path_or_url) as json_file:
            data = json.load(json_file)
        try:
            data = jsonld.expand(data, options={"base": base_url})
        except:
            raise
        finally:
            if not started:
                stop_server(stop)
        if len(data) == 1:
            if "@id" not in data[0] and "id" not in data[0]:
                data[0]["@id"] = base_url + os.path.basename(path_or_url)
    else:
        raise Exception(f"{path_or_url} is not a valid URL or file path")
    return data

# def load_directory(path_or_url, load_file=load_file):
#     """Creates a dictionary mirroring a directory containing only directories and
#     JSON-LD files at the specified path."""

"""
#start the server 

#stop the server
Base URL
directory = {
    
}

"""
#     loaded_directory = {}

#         directory_structure = {}

#     for root, dirs, files in os.walk(base_path):
#         relative_root = os.path.relpath(root, base_path)
#         if relative_root == '.':
#             relative_root = ''

#         subdirs = {}
#         for subdir in dirs:
#             subdir_path = os.path.join(root, subdir)
#             subdirs[subdir] = load_directory_structure(subdir_path, load_jsonld_function)

#         jsonld_files = {}
#         for file in files:
#             if file.endswith('.jsonld'):
#                 file_path = os.path.join(root, file)
#                 jsonld_files[file] = load_jsonld_function(file_path)

#         if relative_root:
#             directory_structure[relative_root] = {'subdirs': subdirs, 'jsonld_files': jsonld_files}
#         else:
#             directory_structure.update(subdirs)
#             directory_structure.update(jsonld_files)

#     return directory_structure
# def load_directory_structure(base_path, started=False, http_kwargs={}):
#     """
#     Recursively iterates over a directory structure and constructs a dictionary.
    
#     Args:
#     - base_path (str): The base directory path to start iterating from.
#     - load_jsonld_function (function): A function that takes a file path and returns the loaded JSON-LD data.
    
#     Returns:
#     - dict: A dictionary with directory names as keys and subdirectory names or loaded JSON-LD as values.
#     """

#     if not started:
#         stop_server(stop) 
#         stop, port = start_server(**http_kwargs)
#         started = True

#     directory_structure = {}

#     for root, dirs, files in os.walk(base_path):
#         relative_root = os.path.relpath(root, base_path)
#         if relative_root == '.':
#             relative_root = ''

#         subdirs = {}
#         for subdir in dirs:
#             subdir_path = os.path.join(root, subdir)
#             subdirs[subdir] = load_directory_structure(subdir_path)

#         jsonld_files = {}
#         for file in files:
#             file_path = os.path.join(root, file)
#             jsonld_files[file] = load_file(file_path, started=True, http_kwargs={"port":port})

#         if relative_root:
#             directory_structure[relative_root] = {'subdirs': subdirs, 'jsonld_files': jsonld_files}
#         else:
#             directory_structure.update(subdirs)
#             directory_structure.update(jsonld_files)


#     stop_server(stop)

#     return directory_structure

def validate_data(data):
    """Validate an expanded jsonld document against the pydantic model.

    Parameters
    ----------
    data : dict
        Python dictionary containing JSONLD object

    Returns
    -------
    conforms: bool
        Whether the document is conformant with the shape
    v_text: str
        Validation errors if any returned by pydantic

    """
    # do we need it?
    # kwargs = {"algorithm": "URDNA2015", "format": "application/n-quads"}
    # normalized = jsonld.normalize(data, kwargs)
    if data[0]["@type"][0] == "http://schema.repronim.org/Field":
        obj_type = Item
    elif data[0]["@type"][0] == "http://schema.repronim.org/ResponseOption":
        obj_type = ResponseOption
    elif data[0]["@type"][0] == "http://schema.repronim.org/Activity":
        obj_type = Activity
    elif data[0]["@type"][0] == "http://schema.repronim.org/Protocol":
        obj_type = Protocol
    elif data[0]["@type"][0] == "http://schema.repronim.org/ResponseActivity":
        obj_type = ResponseActivity
    elif data[0]["@type"][0] == "http://schema.repronim.org/Response":
        obj_type = Response
    else:
        raise ValueError("Unknown type")
    data_fixed = [fixing_old_schema(data[0], copy_data=True)]
    # TODO: where should we load the context from?
    contexfile = Path(__file__).resolve().parent / "models/reproschema"
    with open(contexfile) as fp:
        context = json.load(fp)
    data_fixed_comp = jsonld.compact(data_fixed, context)
    del data_fixed_comp["@context"]
    conforms = False
    v_text = ""
    try:
        obj_type(**data_fixed_comp)
        conforms = True
    except Exception as e:
        v_text = str(e)
    return conforms, v_text


def to_newformat(path, format, prefixfile=None, contextfile=None):
    """Convert a JSONLD document to n-triples format

    Since PyLD requires an http url, a local server is started to serve the
    document.

    Parameters
    ----------
    path : str
        A local path or remote url to convert to n-triples
    format: str of enum
        Returned format jsonld, n-triples, turtle
    prefixfile: str
        Prefixes to use when converting to turtle (ignored otherwise)
    contextfile: str
        Context to use for compaction when returning jsonld. If not provided,
        a jsonld graph is returned.

    Returns
    -------
    normalized : str
        A normalized document

    """
    supported_formats = ["jsonld", "n-triples", "turtle"]
    if format not in supported_formats:
        raise ValueError(f"{format} not in {supported_formats}")
    data = load_file(path)
    if format == "jsonld":
        if contextfile is not None:
            with open(contextfile) as fp:
                context = json.load(fp)
            data = jsonld.compact(data, context)
        return json.dumps(data, indent=2)
    kwargs = {"algorithm": "URDNA2015", "format": "application/n-quads"}
    nt = jsonld.normalize(data, kwargs)
    if format == "n-triples":
        return nt
    import rdflib as rl

    g = rl.Graph()
    g.bind("rs", "http://schema.repronim.org/")
    g.bind("sdo", "http://schema.org/")
    g.bind("nidm", "http://purl.org/nidash/nidm#")
    g.bind("skos", "http://www.w3.org/2004/02/skos/core#")
    g.bind("prov", "http://www.w3.org/ns/prov#")
    if prefixfile is not None:
        with open(prefixfile) as fp:
            prefixes = json.load(fp)
        for key, value in prefixes.items():
            g.bind(key, value)
    g.parse(data=nt, format="nt")
    return g.serialize(format=format)
