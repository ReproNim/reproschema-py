import os

from utils import clean_up
from utils import load_jsons
from utils import output_dir

from reproschema.models.activity import Activity
from reproschema.models.item import Item

activity_dir = output_dir("activities")


def test_default():

    """
    FYI: The default activity does not conform to the schema
    so  `reproschema validate` will complain if you run it in this
    """

    activity = Activity(name="default")
    activity.set_defaults()

    activity.write(activity_dir)

    activity_content, expected = load_jsons(activity_dir, activity)
    assert activity_content == expected

    clean_up(activity_dir, activity)


def test_activity():

    activity = Activity(name="activity1")
    activity.set_defaults()
    activity.set_description("Activity example 1")
    activity.set_pref_label("Example 1")
    activity.set_preamble(
        "Over the last 2 weeks, how often have you been bothered by any of the following problems?"
    )
    activity.set_citation("https://www.ncbi.nlm.nih.gov/pmc/articles/PMC1495268/")
    activity.set_image(
        {"@type": "AudioObject", "contentUrl": "http://example.com/sample-image.png"}
    )
    activity.set_compute("activity1_total_score", "item1 + item2")

    item_1 = Item(name="item1")
    # TODO
    # probably want to have items/item_name be a default
    item_1.URI = os.path.join("items", item_1.at_id)
    # TODO
    # We probably want a method to change those values rather that modifying
    # the instance directly
    item_1.skippable = False
    item_1.required = True
    """
    Items are appended and this updates the  the ``ui`` ``order`` and ``addProperties``
    """
    activity.append_item(item_1)

    item_2 = Item(name="item2")
    item_2.set_filename("item_two")

    """
    In this case the URI is relative to where the activity file will be saved
    """
    item_2.URI = os.path.join("..", "other_dir", item_2.at_id)
    item_2.required = True
    activity.append_item(item_2)

    """
    By default all files are save with a jsonld extension but this can be changed
    """
    item_3 = Item(name="activity1_total_score", ext="")
    item_3.URI = os.path.join("items", item_3.at_id)
    item_3.skippable = False
    item_3.required = True
    item_3.visible = False
    activity.append_item(item_3)

    activity.write(activity_dir)
    activity_content, expected = load_jsons(activity_dir, activity)
    assert activity_content == expected

    clean_up(activity_dir, activity)
