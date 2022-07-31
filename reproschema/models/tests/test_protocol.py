import os
from pathlib import Path

from reproschema.models.activity import Activity
from reproschema.models.protocol import Protocol

my_path = Path(__file__).resolve().parent

from utils import load_jsons, clean_up, output_dir

protocol_dir = output_dir("protocols")


def test_default():

    """
    FYI: The default protocol does not conform to the schema
    so  `reproschema validate` will complain if you run it in this
    """

    protocol = Protocol(name="default")
    protocol.set_defaults()
    protocol.write(protocol_dir)

    protocol_content, expected = load_jsons(protocol_dir, protocol)
    assert protocol_content == expected

    clean_up(protocol_dir, protocol)


def test_protocol():

    protocol = Protocol(name="protocol1")
    protocol.set_defaults()
    protocol.set_pref_label(pref_label="Protocol1", lang="en")
    protocol.set_description("example Protocol")
    protocol.set_landing_page("http://example.com/sample-readme.md")

    auto_advance = True
    allow_export = True
    disable_back = True
    protocol.set_ui_allow(auto_advance, allow_export, disable_back)

    activity_1 = Activity()
    activity_1.set_defaults("activity1")
    activity_1.set_pref_label("Screening")
    activity_1.URI = os.path.join("..", "activities", activity_1.at_id)
    protocol.append_activity(activity_1)

    protocol.write(protocol_dir)

    protocol_content, expected = load_jsons(protocol_dir, protocol)
    assert protocol_content == expected

    clean_up(protocol_dir, protocol)
