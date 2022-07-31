import json
from pathlib import Path

my_path = Path(__file__).resolve().parent


def load_jsons(dir, obj):

    output_file = Path(dir).joinpath(obj.at_id)
    content = read_json(output_file)

    data_file = my_path.joinpath("data", Path(dir).name, obj.at_id)
    expected = read_json(data_file)

    return content, expected


def read_json(file):

    with open(file, "r") as ff:
        return json.load(ff)


def clean_up(dir, obj):
    Path(dir).joinpath(obj.at_id).unlink()


def output_dir(dir):
    value = my_path.joinpath(dir)
    if not value.is_dir():
        value.mkdir(parents=True, exist_ok=True)
    return value
