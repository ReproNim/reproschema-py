import os, sys, json

from ..protocol import Protocol
from ..activity import Activity

my_path = os.path.dirname(os.path.abspath(__file__))

# Left here in case Remi and python path or import can't be friends once again.
# sys.path.insert(0, my_path + "/../")

# TODO
# refactor across the different test modules
protocol_dir = os.path.join(my_path, "protocols")
if not os.path.exists(protocol_dir):
    os.makedirs(os.path.join(protocol_dir))

"""
Only for the few cases when we want to check against some of the files in
reproschema/tests/data
"""
reproschema_test_data = os.path.join(my_path, "..", "..", "tests", "data")


def test_default():

    """
    FYI: The default protocol does not conform to the schema
    so  `reproschema validate` will complain if you run it in this
    """

    protocol = Protocol()
    protocol.set_defaults()

    protocol.write(protocol_dir)
    protocol_content, expected = load_jsons(protocol)
    assert protocol_content == expected

    clean_up(protocol)


def test_protocol():

    protocol = Protocol()
    protocol.set_defaults("protocol1")
    protocol.set_pref_label("Protocol1")
    protocol.set_description("example Protocol")
    protocol.set_landing_page("http://example.com/sample-readme.md")

    auto_advance = True
    allow_export = True
    disable_back = True
    protocol.set_ui_allow(auto_advance, allow_export, disable_back)

    activity_1 = Activity()
    activity_1.set_defaults("activity1")
    activity_1.set_pref_label("Screening")
    activity_1.set_URI(os.path.join("..", "activities", activity_1.get_filename()))
    protocol.append_activity(activity_1)

    protocol.write(protocol_dir)
    protocol_content, expected = load_jsons(protocol)
    assert protocol_content == expected

    clean_up(protocol)


"""
HELPER FUNCTIONS
"""


def load_jsons(obj):

    output_file = os.path.join(protocol_dir, obj.get_filename())
    content = read_json(output_file)

    data_file = os.path.join(my_path, "data", "protocols", obj.get_filename())
    expected = read_json(data_file)

    return content, expected


def read_json(file):

    with open(file, "r") as ff:
        return json.load(ff)


def clean_up(obj):
    os.remove(os.path.join(protocol_dir, obj.get_filename()))
