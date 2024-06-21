import os
import threading
from copy import deepcopy
from http.server import HTTPServer, SimpleHTTPRequestHandler
from tempfile import mkdtemp

import requests_cache

from . import get_logger

lgr = get_logger()


class LoggingRequestHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        lgr.debug(format % args)


def simple_http_server(host="localhost", port=4001, path="."):
    """
    From: https://stackoverflow.com/a/38943044
    """

    server = HTTPServer((host, port), LoggingRequestHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.deamon = True

    cwd = os.getcwd()

    def start():
        os.chdir(path)
        thread.start()
        lgr.debug("starting server on port {}".format(server.server_port))

    def stop():
        os.chdir(cwd)
        server.shutdown()
        server.socket.close()
        lgr.debug("stopping server on port {}".format(server.server_port))

    return start, stop, port


def start_server(port=8000, path=None, tmpdir=None):
    if path is None:
        path = os.getcwd()
    requests_cache.install_cache(tmpdir or mkdtemp())
    start, stop, port = simple_http_server(port=port, path=path)
    start()
    return stop, port


def stop_server(stop):
    stop()
    requests_cache.clear()


# items that have to be fixed in the old schema
LANG_FIX = [
    "http://schema.org/schemaVersion",
    "http://schema.org/version",
    "http://schema.repronim.org/limit",
    "http://schema.repronim.org/randomMaxDelay",
    "http://schema.org/inLanguage",
    "http://schema.repronim.org/schedule",
]
BOOL_FIX = [
    "http://schema.repronim.org/shuffle",
    "http://schema.org/readonlyValue",
    "http://schema.repronim.org/multipleChoice",
    "http://schema.org/valueRequired",
]

ALLOWTYPE_FIX = ["http://schema.repronim.org/allow"]
ALLOWTYPE_MAPPING = {
    "http://schema.repronim.org/Skipped": "http://schema.repronim.org/AllowSkip",
    "http://schema.repronim.org/DontKnow": "http://schema.repronim.org/AllowAltResponse",
}

IMAGE_FIX = ["http://schema.org/image"]


def _lang_fix(data_el):
    if isinstance(data_el, dict):
        data_el.pop("@language", None)
    elif isinstance(data_el, list) and len(data_el) == 1:
        data_el = data_el[0]
        data_el.pop("@language", None)
    else:
        raise Exception(f"expected a list or dictionary, got {data_el}")
    return data_el


def _image_fix(data_el):
    if isinstance(data_el, dict):
        if "@id" not in data_el and "@value" in data_el:
            data_el["@id"] = data_el.pop("@value")
            data_el.pop("@language", None)
    elif isinstance(data_el, list) and len(data_el) == 1:
        data_el = data_el[0]
        data_el = _image_fix(data_el)
    else:
        raise Exception(f"expected a list or dictionary, got {data_el}")
    return data_el


def _bool_fix(data_el):
    if isinstance(data_el, dict):
        data_el["@type"] = "http://www.w3.org/2001/XMLSchema#boolean"
    elif isinstance(data_el, list):
        for el in data_el:
            _bool_fix(el)
    else:
        raise Exception(f"expected a list or dictionary, got {data_el}")


def _allowtype_fix(data_el):
    if isinstance(data_el, dict):
        if data_el["@id"] in ALLOWTYPE_MAPPING:
            data_el["@id"] = ALLOWTYPE_MAPPING[data_el["@id"]]
    elif isinstance(data_el, list):
        for el in data_el:
            _allowtype_fix(el)
    else:
        raise Exception(f"expected a list or dictionary, got {data_el}")


def fixing_old_schema(data, copy_data=False):
    """Fixes the old schema so it can be load to the new model"""
    if copy_data:
        data = deepcopy(data)
    for key, val in data.items():
        if key in LANG_FIX:
            data[key] = _lang_fix(val)
        elif key in BOOL_FIX:
            _bool_fix(val)
        elif key in ALLOWTYPE_FIX:
            _allowtype_fix(val)
        elif key in IMAGE_FIX:
            data[key] = _image_fix(val)
        elif isinstance(val, (str, bool, int, float)):
            pass
        elif isinstance(val, dict):
            fixing_old_schema(val)
        elif isinstance(val, list):
            for el in val:
                if isinstance(el, (str, bool, int, float)):
                    pass
                elif isinstance(el, dict):
                    fixing_old_schema(el)
                else:
                    raise Exception(
                        f"expected a list, str, bool or numerics, got {data_el}"
                    )
        else:
            raise Exception(f"type {type(val)} not supported yet")
    return data
