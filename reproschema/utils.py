import os
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from tempfile import mkdtemp
import requests
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
