import os
from ..validate import validate_dir


def test_validate():
    os.chdir(os.path.dirname(__file__))
    assert validate_dir("data", os.path.abspath("validation"))
