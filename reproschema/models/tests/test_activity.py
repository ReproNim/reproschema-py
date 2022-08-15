import os
from unittest import skip

from utils import clean_up
from utils import load_jsons
from utils import output_dir

from reproschema.models.activity import Activity
from reproschema.models.item import Item

activity_dir = output_dir("activities")


def test_default():

    """
    FYI: The default activity does not conform to the schema
    so  `reproschema validate` will complain if you run it on this
    """

    activity = Activity(name="default", output_dir=activity_dir)
    activity.write()

    activity_content, expected = load_jsons(activity_dir, activity)
    assert activity_content == expected

    clean_up(activity_dir, activity)


def test_activity():

    activity = Activity(
        name="activity1",
        prefLabel="Example 1",
        description="Activity example 1",
        citation="https://www.ncbi.nlm.nih.gov/pmc/articles/PMC1495268/",
        output_dir=activity_dir,
    )
    activity.set_preamble(
        "Over the last 2 weeks, how often have you been bothered by any of the following problems?"
    )
    activity.image = {
        "@type": "AudioObject",
        "contentUrl": "http://example.com/sample-image.png",
    }

    activity.set_compute("activity1_total_score", "item1 + item2")

    item_1 = Item(name="item1", skippable=False, required=True, output_dir="items")

    item_2 = Item(
        name="item2", required=True, output_dir=os.path.join("..", "other_dir")
    )
    item_2.set_filename("item_two")

    """
    By default all files are save with a jsonld extension but this can be changed
    """
    item_3 = Item(
        name="activity1_total_score",
        ext="",
        skippable=False,
        required=True,
        visible=False,
        output_dir="items",
    )

    activity.append_item(item_1)
    activity.append_item(item_2)
    activity.append_item(item_3)

    activity.write()
    activity_content, expected = load_jsons(activity_dir, activity)
    assert activity_content == expected

    clean_up(activity_dir, activity)


def test_activity_1():

    activity = Activity(
        name="activity1",
        prefLabel="Example 1",
        description="Activity example 1",
        citation="https://www.ncbi.nlm.nih.gov/pmc/articles/PMC1495268/",
        output_dir=activity_dir,
        suffix="",
    )
    activity.set_preamble(
        preamble="Over the last 2 weeks, how often have you been bothered by any of the following problems?"
    )
    activity.set_preamble(
        preamble="Durante las últimas 2 semanas, ¿con qué frecuencia le han molestado los siguintes problemas?",
        lang="es",
    )
    activity.image = {
        "@type": "AudioObject",
        "contentUrl": "http://example.com/sample-image.png",
    }
    activity.at_context = "../../contexts/generic"
    activity.ui.AutoAdvance = False
    activity.ui.AllowExport = False
    activity.update()

    activity.set_compute(variable="activity1_total_score", expression="item1 + item2")

    item_1 = Item(name="item1", skippable=False, required=True, output_dir="items")
    item_1.prefLabel = {}
    activity.update()

    item_2 = Item(name="item2", skippable=True, required=True, output_dir="items")
    item_2.set_filename("item2")
    item_2.prefLabel = {}
    activity.update()

    item_3 = Item(
        name="activity1_total_score",
        ext="",
        skippable=False,
        required=True,
        visible=False,
        output_dir="items",
    )
    item_3.prefLabel = {}
    activity.update()

    activity.append_item(item_1)
    activity.append_item(item_2)
    activity.append_item(item_3)

    activity.write()
    activity_content, expected = load_jsons(activity_dir, activity)
    assert activity_content == expected

    clean_up(activity_dir, activity)
