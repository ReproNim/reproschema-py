from pyld import jsonld
import json
import os
from pathlib import Path
from copy import deepcopy
from .utils import start_server, stop_server, lgr, fixing_old_schema
from .models import Item, Activity, Protocol, ResponseOption


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
