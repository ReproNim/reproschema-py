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

    protocol = Protocol(name="default", output_dir=protocol_dir)
    protocol.write()

    protocol_content, expected = load_jsons(protocol_dir, protocol)
    assert protocol_content == expected

    clean_up(protocol_dir, protocol)


def test_protocol():

    protocol = Protocol(
        name="protocol1",
        prefLabel="Protocol1",
        lang="en",
        description="example Protocol",
        output_dir=protocol_dir,
    )
    protocol.set_preamble(preamble="protocol1", lang="en")
    protocol.set_landing_page(page="http://example.com/sample-readme.md")
    protocol.ui.AutoAdvance = True
    protocol.ui.AllowExport = True
    protocol.ui.DisableBack = True
    protocol.update()

    activity_1 = Activity(
        name="activity1",
        prefLabel="Screening",
        lang="en",
        output_dir=os.path.join("..", "activities"),
    )

    protocol.append_activity(activity_1)

    protocol.write()

    protocol_content, expected = load_jsons(protocol_dir, protocol)
    assert protocol_content == expected

    clean_up(protocol_dir, protocol)


def test_protocol_1():

    protocol = Protocol(
        name="protocol1",
        prefLabel="Protocol1",
        lang="en",
        description="example Protocol",
        output_dir=protocol_dir,
        suffix="",
    )
    protocol.set_pref_label(pref_label="Protocol1_es", lang="es")
    protocol.set_landing_page(page="http://example.com/sample-readme.md", lang="en")
    protocol.ui.AutoAdvance = True
    protocol.ui.AllowExport = True
    protocol.ui.DisableBack = True
    protocol.at_context = "../../contexts/generic"
    protocol.update()

    activity_1 = Activity(
        name="activity1",
        prefLabel="Screening",
        lang="en",
        suffix="",
        output_dir=os.path.join("..", "activities"),
        visible=True,
        skippable=False,
        required=None,
    )

    activity_1.ui.shuffle = False
    activity_1.update()
    activity_1.set_pref_label(pref_label="Screening_es", lang="es")

    protocol.append_activity(activity_1)

    protocol.write()

    protocol_content, expected = load_jsons(protocol_dir, protocol)
    assert protocol_content == expected

    clean_up(protocol_dir, protocol)
