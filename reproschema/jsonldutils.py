import json
import os
from urllib.parse import urlparse

import requests
from pyld import jsonld

from .context_url import CONTEXTFILE_URL
from .models import identify_model_class
from .utils import fixing_old_schema, lgr, start_server, stop_server


def _is_url(path):
    """
    Determine whether the given path is a URL.
    """
    parsed = urlparse(str(path))
    return parsed.scheme in ("http", "https", "ftp", "ftps")


def _is_file(path):
    """
    Determine whether the given path is a valid file path.
    """
    return os.path.isfile(path)


def _fetch_jsonld_context(url):
    response = requests.get(url)
    return response.json()


def load_file(
    path_or_url,
    started=False,
    http_kwargs=None,
    compact=False,
    compact_context=None,
    fixoldschema=False,
):
    """Load a file or URL and return the expanded JSON-LD data."""
    path_or_url = str(path_or_url)
    if http_kwargs is None:
        http_kwargs = {}
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
            try:
                data = json.load(json_file)
            except json.JSONDecodeError as e:
                raise json.JSONDecodeError(
                    f"Error parsing JSON file {json_file}: {e.msg}",
                    e.doc,
                    e.pos,
                ) from e
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

    if isinstance(data, list) and len(data) == 1:
        data = data[0]

    if fixoldschema:
        data = fixing_old_schema(data, copy_data=True)
    if compact:
        if compact_context:
            if _is_file(compact_context):
                with open(compact_context) as fp:
                    context = json.load(fp)
            elif _is_url(compact_context):
                context = _fetch_jsonld_context(compact_context)
            else:
                raise Exception(
                    f"compact_context has tobe a file or url, but {compact_context} provided"
                )
        if _is_file(path_or_url):
            data = jsonld.compact(
                data, ctx=context, options={"base": base_url}
            )
        else:
            data = jsonld.compact(data, ctx=context)

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
    obj_type = identify_model_class(data["@type"][0])
    data_fixed = [fixing_old_schema(data, copy_data=True)]
    context = _fetch_jsonld_context(CONTEXTFILE_URL)
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
