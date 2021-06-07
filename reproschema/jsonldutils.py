from pyld import jsonld
from pyshacl import validate as shacl_validate
import json
import os
from .utils import start_server, stop_server, lgr


def load_file(path_or_url, started=False, http_kwargs={}):
    try:
        data = jsonld.expand(path_or_url)
        if len(data) == 1:
            if "@id" not in data[0]:
                data[0]["@id"] = path_or_url
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
                if "@id" not in data[0]:
                    data[0]["@id"] = base_url + os.path.basename(path_or_url)
        else:
            raise
    return data


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
    return g.serialize(format=format).decode()
