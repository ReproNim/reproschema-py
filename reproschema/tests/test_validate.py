import os
from ..validate import validate_dir, validate
import pytest


def test_validate():
    os.chdir(os.path.dirname(__file__))
    assert validate_dir("data", os.path.abspath("reproschema-shacl.ttl"))


def test_type_error():
    os.chdir(os.path.dirname(__file__))
    with pytest.raises(ValueError):
        validate_dir("contexts", os.path.abspath("reproschema-shacl.ttl"))


def test_url():
    url = "https://raw.githubusercontent.com/ReproNim/reproschema/1.0.0-rc1/examples/activities/activity1.jsonld"
    assert validate(os.path.abspath("reproschema-shacl.ttl"), url)
