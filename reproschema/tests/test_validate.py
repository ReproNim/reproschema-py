from glob import glob
import os


def test_validate(tmpdir):
    files = glob(os.path.join(os.path.dirname(__file__), "data", "*.json"))
    assert len(files) == 0
