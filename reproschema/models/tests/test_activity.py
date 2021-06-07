import os, sys, json

from ..activity import Activity
from ..item import Item

my_path = os.path.dirname(os.path.abspath(__file__))

# Left here in case Remi and python path or import can't be friends once again.
# sys.path.insert(0, my_path + "/../")

# TODO
# refactor across the different test modules
activity_dir = os.path.join(my_path, "activities")
if not os.path.exists(activity_dir):
    os.makedirs(os.path.join(activity_dir))

"""
Only for the few cases when we want to check against some of the files in
reproschema/tests/data
"""
reproschema_test_data = os.path.join(my_path, "..", "..", "tests", "data")


def test_default():

    """
    FYI: The default activity does not conform to the schema
    so  `reproschema validate` will complain if you run it in this
    """

    activity = Activity()
    activity.set_defaults()

    activity.write(activity_dir)
    activity_content, expected = load_jsons(activity)
    assert activity_content == expected

    clean_up(activity)


def test_activity():

    activity = Activity()
    activity.set_defaults("activity1")
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

    item_1 = Item()
    item_1.set_defaults("item1")
    # TODO
    # probably want to have items/item_name be a default
    item_1.set_URI(os.path.join("items", item_1.get_filename()))
    # TODO
    # We probably want a method to change those values rather that modifying
    # the instance directly
    item_1.skippable = False
    item_1.required = True
    """
    Items are appended and this updates the  the ``ui`` ``order`` and ``addProperties``
    """
    activity.append_item(item_1)

    item_2 = Item()
    item_2.set_defaults("item2")
    item_2.set_filename("item_two")

    """
    In this case the URI is relative to where the activity file will be saved
    """
    item_2.set_URI(os.path.join("..", "other_dir", item_2.get_filename()))
    item_2.required = True
    activity.append_item(item_2)

    item_3 = Item()
    item_3.set_defaults("activity1_total_score")
    """
    By default all files are save with a json.ld extension but this can be changed
    """
    file_ext = ""
    item_3.set_filename("activity1_total_score", file_ext)
    item_3.set_URI(os.path.join("items", item_3.get_filename()))
    item_3.skippable = False
    item_3.required = True
    item_3.visible = False
    activity.append_item(item_3)

    activity.write(activity_dir)
    activity_content, expected = load_jsons(activity)
    assert activity_content == expected

    clean_up(activity)


"""
HELPER FUNCTIONS
"""


def load_jsons(obj):

    output_file = os.path.join(activity_dir, obj.get_filename())
    content = read_json(output_file)

    data_file = os.path.join(my_path, "data", "activities", obj.get_filename())
    expected = read_json(data_file)

    return content, expected


def read_json(file):

    with open(file, "r") as ff:
        return json.load(ff)


def clean_up(obj):
    os.remove(os.path.join(activity_dir, obj.get_filename()))
