import os, sys, json

from ..activity import Activity
from ..item import Item

my_path = os.path.dirname(os.path.abspath(__file__))

# sys.path.insert(0, my_path + "/../")

activity_dir = os.path.join(my_path, "activities")
if not os.path.exists(activity_dir):
    os.makedirs(os.path.join(activity_dir))

reproschema_test_data = os.path.join(my_path, "..", "..", "tests", "data")


def test_default():

    """
    FYI: The default activity does not conform to the schema
    """

    activity = Activity()
    activity.set_defaults()

    activity.write(activity_dir)
    activity_content, expected = load_jsons(activity)
    assert activity_content == expected


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
    # probably want to have items/item_name be a default
    item_1.set_URI(os.path.join("items", item_1.get_filename()))
    item_1.skippable = False
    activity.append_item(item_1)

    item_2 = Item()
    item_2.set_defaults("item2")
    item_2.set_URI(os.path.join("items", item_2.get_filename()))
    activity.append_item(item_2)

    item_3 = Item()
    item_3.set_defaults("activity1_total_score")
    item_3.set_filename("activity1_total_score", "")
    item_3.set_URI(os.path.join("items", item_3.get_filename()))
    item_3.skippable = False
    item_3.visible = False
    activity.append_item(item_3)

    activity.write(activity_dir)
    activity_content, expected = load_jsons(activity)
    assert activity_content == expected


def load_jsons(obj):

    output_file = os.path.join(activity_dir, obj.get_filename())
    content = read_json(output_file)

    data_file = os.path.join(my_path, "data", "activities", obj.get_filename())
    expected = read_json(data_file)

    return content, expected


def read_json(file):

    with open(file, "r") as ff:
        return json.load(ff)
