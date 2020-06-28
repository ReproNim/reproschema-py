import os
from ..validate import validate_dir, validate
import pytest


def test_validate():
    os.chdir(os.path.dirname(__file__))
    assert validate_dir("data", os.path.abspath("validation"))


def test_type_error():
    os.chdir(os.path.dirname(__file__))
    with pytest.raises(ValueError):
        validate_dir("contexts", os.path.abspath("validation"))


def test_url():
    url = "https://raw.githubusercontent.com/ReproNim/reproschema-py/master/reproschema/tests/data/activities/activity1.jsonld"
    assert validate(os.path.abspath("validation"), url)
