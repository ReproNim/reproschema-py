from pyld import jsonld
from pyshacl import validate as shacl_validate
import json
import os
from .utils import start_server, stop_server, lgr


def load_file(path_or_url, started=False, http_kwargs={}):
    try:
        data = jsonld.expand(path_or_url)
    except jsonld.JsonLdError as e:
        if 'only "http" and "https"' in str(e):
            lgr.debug("Reloading with local server")
            root = os.path.dirname(path_or_url)
            if not started:
                stop, port = start_server(**http_kwargs)
            else:
                if "port" not in http_kwargs:
                    raise KeyError("port key missing in http_kwargs")
                port = http_kwargs["port"]
            base_url = f"http://localhost:{port}/{root}/"
            with open(path_or_url) as json_file:
                data = json.load(json_file)
            try:
                data = jsonld.expand(data, options={"base": base_url})
            except:
                raise
            finally:
                if not started:
                    stop_server(stop)
        else:
            raise
    return data


def file2shape(filename, shape_dir, started, http_kwargs={}):
    data = load_file(filename, started, http_kwargs)
    no_type = True
    shape_file_path = []
    for val in data:
        if "@type" not in val:
            continue
        for schema_type in val["@type"]:
            for key in ["Protocol", "Activity", "Field", "ResponseOption"]:
                if schema_type.endswith(f"/{key}"):
                    shape_file_path.append(os.path.join(shape_dir, f"{key}Shape.ttl"))
                    no_type = False
    if no_type:
        raise ValueError(f"{filename} missing @type")
    if len(shape_file_path) > 1:
        raise ValueError(
            f"Multiple reproschema types in {filename}. Not " f"supported yet"
        )
    return data, shape_file_path.pop()


def validate_data(data, shape_file_path):
    """Validate an expanded jsonld document against a shape.

    Parameters
    ----------
    data : dict
        Python dictionary containing JSONLD object
    shape_file_path : str
        SHACL file for the document

    Returns
    -------
    conforms: bool
        Whether the document is conformant with the shape
    v_text: str
        Validation information returned by PySHACL

    """
    kwargs = {"algorithm": "URDNA2015", "format": "application/n-quads"}
    normalized = jsonld.normalize(data, kwargs)
    data_file_format = "nquads"
    shape_file_format = "turtle"
    conforms, v_graph, v_text = shacl_validate(
        normalized,
        shacl_graph=shape_file_path,
        data_graph_format=data_file_format,
        shacl_graph_format=shape_file_format,
        inference="rdfs",
        debug=False,
        serialize_report_graph=True,
    )
    return conforms, v_text


def to_newformat(path, format):
    """Convert a JSONLD document to n-triples format

    Since PyLD requires an http url, a local server is started to serve the
    document.

    Parameters
    ----------
    path : str
        A local path or remote url to convert to n-triples
    format: str of enum
        Returned format jsonld, n-triples, turtle

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
        return json.dumps(data, indent=2)
    kwargs = {"algorithm": "URDNA2015", "format": "application/n-quads"}
    nt = jsonld.normalize(data, kwargs)
    if format == "n-triples":
        return nt
    import rdflib as rl

    g = rl.Graph()
    g.parse(data=nt, format="nt")
    return g.serialize(format=format).decode()
