import os

import pytest

from ..validate import validate, validate_dir


def test_validate():
    os.chdir(os.path.dirname(__file__))
    assert validate_dir("data")


def test_type_error():
    os.chdir(os.path.dirname(__file__))
    with pytest.raises(ValueError):
        validate_dir("contexts")


def test_url():
    url = "https://raw.githubusercontent.com/ReproNim/reproschema/1.0.0-rc1/examples/activities/activity1.jsonld"
    assert validate(url)
