import os, sys, json

from ..item import Item, ResponseOption

my_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, my_path + "/../")

item_dir = os.path.join(my_path, "items")
if not os.path.exists(item_dir):
    os.makedirs(os.path.join(item_dir))

# integer
# float
# select
# multiradio
# multiselect
# char
# time range
# date
# slider
# language


def test_default():

    item = Item()
    item.set_defaults()
    item.write(item_dir)

    item_content, expected = load_jsons(item)

    assert item_content == expected


def test_text():

    item = Item("1.0.0-rc4")
    item.set_defaults("text")
    item.set_input_type_as_text(100)

    item.set_question("question for text item", "en")

    item.write(item_dir)

    item_content, expected = load_jsons(item)

    assert item_content == expected


def test_float():

    item = Item("1.0.0-rc4")
    item.set_defaults("float")
    item.set_description("This is a float item.")
    item.set_input_type_as_float()
    item.set_question("This is an item where the user can input a float.", "en")

    item.write(item_dir)

    item_content, expected = load_jsons(item)

    assert item_content == expected


def test_integer():

    item = Item()
    item.set_defaults("integer")
    item.set_description("This is a integer item.")
    item.set_input_type_as_int()
    item.set_question("This is an item where the user can input a integer.", "en")

    item.write(item_dir)

    item_content, expected = load_jsons(item)

    assert item_content == expected


def test_radio():

    item = Item("1.0.0-rc4")
    item.set_defaults("radio")

    item.set_question("question for radio item", "en")

    response_options = ResponseOption()
    response_options.set_type("int")
    response_options.add_choice({"name": {"en": "Not at all"}, "value": 0})
    response_options.add_choice({"name": {"en": "Several days"}, "value": 1})
    response_options.set_max(1)

    item.set_input_type_as_radio(response_options)

    item.write(item_dir)

    item_content, expected = load_jsons(item)

    assert item_content == expected


def load_jsons(item):
    output_file = os.path.join(item_dir, item.get_filename())
    item_content = read_json(output_file)

    data_file = os.path.join(my_path, "data", "items", item.get_filename())
    expected = read_json(data_file)

    return item_content, expected


def read_json(file):

    with open(file, "r") as ff:
        return json.load(ff)
