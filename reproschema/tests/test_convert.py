import os
from ..jsonldutils import to_newformat
import pytest


@pytest.fixture
def filename():
    ldfile = os.path.join(
        os.path.dirname(__file__), "data", "protocols", "protocol1.jsonld"
    )
    cwd = os.getcwd()
    ldfile = ldfile.replace(f"{cwd}/", "")
    return ldfile


def test_jsonld(filename):
    value = to_newformat(filename, "jsonld")
    import json

    json.loads(value)


def test_ntriples(filename):
    value = to_newformat(filename, "n-triples")
    for line in value.splitlines():
        if line:
            assert line.strip().endswith(".")


def test_turtle(filename):
    value = to_newformat(filename, "turtle")
    import rdflib as rl

    g = rl.Graph()
    g.parse(data=value, format="turtle")


def test_type_error(filename):
    with pytest.raises(ValueError):
        to_newformat(filename, "snapturtle")


def test_convert_url():
    url = "https://raw.githubusercontent.com/ReproNim/reproschema-py/master/reproschema/tests/data/activities/activity1.jsonld"
    value = to_newformat(url, "turtle")
    import rdflib as rl

    g = rl.Graph()
    g.parse(data=value, format="turtle")
