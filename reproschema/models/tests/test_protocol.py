import os, sys, json

from ..protocol import Protocol
from ..activity import Activity

my_path = os.path.dirname(os.path.abspath(__file__))

# sys.path.insert(0, my_path + "/../")

protocol_dir = os.path.join(my_path, "protocols")
if not os.path.exists(protocol_dir):
    os.makedirs(os.path.join(protocol_dir))

reproschema_test_data = os.path.join(my_path, "..", "..", "tests", "data")


def test_default():

    protocol = Protocol()
    protocol.set_defaults()

    protocol.write(protocol_dir)
    protocol_content, expected = load_jsons(protocol)
    assert protocol_content == expected


# def test_protocol():


def load_jsons(obj):

    output_file = os.path.join(protocol_dir, obj.get_filename())
    content = read_json(output_file)

    data_file = os.path.join(my_path, "data", "protocols", obj.get_filename())
    expected = read_json(data_file)

    return content, expected


def read_json(file):

    with open(file, "r") as ff:
        return json.load(ff)
