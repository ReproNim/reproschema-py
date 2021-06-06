import os, sys, json

from ..item import ResponseOption

my_path = os.path.dirname(os.path.abspath(__file__))

# sys.path.insert(0, my_path + "/../")

response_options_dir = os.path.join(my_path, "response_options")
if not os.path.exists(response_options_dir):
    os.makedirs(os.path.join(response_options_dir))

reproschema_test_data = os.path.join(my_path, "..", "..", "tests", "data")


def test_default():

    response_options = ResponseOption()
    response_options.set_defaults()

    response_options.write(response_options_dir)
    content, expected = load_jsons(response_options)
    assert content == expected


def test_example():

    response_options = ResponseOption()
    response_options.set_defaults()
    response_options.set_filename("example")
    response_options.set_type("integer")
    response_options.unset("multipleChoice")
    response_options.add_choice("Not at all", 0)
    for i in range(1, 5):
        response_options.add_choice("", i)
    response_options.add_choice("Completely", 6)
    response_options.set_max(6)

    response_options.write(response_options_dir)
    content, expected = load_jsons(response_options)
    assert content == expected


def load_jsons(obj):

    output_file = os.path.join(response_options_dir, obj.get_filename())
    content = read_json(output_file)

    data_file = os.path.join(my_path, "data", "response_options", obj.get_filename())
    expected = read_json(data_file)

    return content, expected


def read_json(file):

    with open(file, "r") as ff:
        return json.load(ff)
