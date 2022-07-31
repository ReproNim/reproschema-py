import os
from pathlib import Path

from utils import clean_up
from utils import load_jsons
from utils import output_dir
from utils import read_json

from reproschema.models.item import Item
from reproschema.models.item import ResponseOption

item_dir = output_dir("items")


def test_default():

    item = Item(name="default")

    item.write(item_dir)
    item_content, expected = load_jsons(item_dir, item)
    assert item_content == expected

    clean_up(item_dir, item)


# TODO
# many items types (audio ones for examples) are not yet tested because the code cannot yet generate them.

"""
text items
"""


def test_text():

    item = Item(name="text", question="question for text item", input_type="text")

    item.write(item_dir)
    item_content, expected = load_jsons(item_dir, item)
    assert item_content == expected

    clean_up(item_dir, item)


def test_multitext():

    text_length = 50

    item = Item(name="multitext")
    item.set_input_type_as_multitext(text_length)

    item.set_question("This is an item where the user can input several text field.")

    item.write(item_dir)
    item_content, expected = load_jsons(item_dir, item)
    assert item_content == expected

    clean_up(item_dir, item)


"""
items with a specific "type"
"""


def test_email():

    item = Item(name="email", question="input email address", input_type="email")

    item.write(item_dir)
    item_content, expected = load_jsons(item_dir, item)
    assert item_content == expected

    clean_up(item_dir, item)


def test_participant_id():

    item = Item(
        name="participant id",
        question="input the participant id number",
        input_type="id",
    )

    item.write(item_dir)
    item_content, expected = load_jsons(item_dir, item)
    assert item_content == expected

    clean_up(item_dir, item)


def test_date():

    item = Item(name="date", question="input a date", input_type="date")

    item.write(item_dir)
    item_content, expected = load_jsons(item_dir, item)
    assert item_content == expected

    clean_up(item_dir, item)


def test_time_range():

    item = Item(
        name="time range", question="input a time range", input_type="time_range"
    )

    item.write(item_dir)
    item_content, expected = load_jsons(item_dir, item)
    assert item_content == expected

    clean_up(item_dir, item)


def test_year():

    item = Item(name="year", question="input a year", input_type="year")

    item.write(item_dir)
    item_content, expected = load_jsons(item_dir, item)
    assert item_content == expected

    clean_up(item_dir, item)


"""
Items that refer to a preset list of responses choices
"""


def test_language():

    item = Item(
        name="language",
        question="This is an item where the user can select several language.",
        input_type="language",
    )

    item.write(item_dir)
    item_content, expected = load_jsons(item_dir, item)
    assert item_content == expected

    clean_up(item_dir, item)


def test_country():

    item = Item(name="country", question="select a country", input_type="country")

    item.write(item_dir)
    item_content, expected = load_jsons(item_dir, item)
    assert item_content == expected

    clean_up(item_dir, item)


def test_state():

    item = Item(name="state", question="select a USA state", input_type="state")

    item.write(item_dir)
    item_content, expected = load_jsons(item_dir, item)
    assert item_content == expected

    clean_up(item_dir, item)


"""
NUMERICAL ITEMS
"""


def test_float():

    item = Item(
        name="float",
        question="This is an item where the user can input a float.",
        input_type="float",
    )
    item.set_description("This is a float item.")

    item.write(item_dir)
    item_content, expected = load_jsons(item_dir, item)
    assert item_content == expected

    clean_up(item_dir, item)


def test_integer():

    item = Item(
        name="integer",
        question="This is an item where the user can input a integer.",
        input_type="int",
    )
    item.set_description("This is a integer item.")

    item.write(item_dir)
    item_content, expected = load_jsons(item_dir, item)
    assert item_content == expected

    clean_up(item_dir, item)


"""
SELECTION ITEMS: radio and select
tested both with:
- only one response allowed
- multiple responses allowed
"""


def test_radio():

    item = Item(name="radio", question="question for radio item")

    response_options = ResponseOption()
    response_options.add_choice("Not at all", 0, "en")
    response_options.add_choice("Several days", 1, "en")
    # TODO
    # set_min and set_max cold probably be combined into a single method that gets
    # those values from the content of the choice key
    response_options.set_max(1)

    item.set_input_type_as_radio(response_options)

    item.write(item_dir)
    item_content, expected = load_jsons(item_dir, item)
    assert item_content == expected

    clean_up(item_dir, item)

    item.set_filename("radio multiple")
    item.set_description("radio multiple")
    item.set_pref_label("radio multiple")
    item.set_question("question for radio item with multiple responses")
    response_options.set_multiple_choice(True)
    item.set_input_type_as_radio(response_options)
    item.write(item_dir)

    item_content, expected = load_jsons(item_dir, item)
    assert item_content == expected

    clean_up(item_dir, item)


def test_select():

    item = Item(name="select", question="question for select item")

    response_options = ResponseOption()
    response_options.add_choice("Response option 1", 0)
    response_options.add_choice("Response option 2", 1)
    response_options.add_choice("Response option 3", 2)
    response_options.set_max(2)

    item.set_input_type_as_select(response_options)

    item.write(item_dir)
    item_content, expected = load_jsons(item_dir, item)
    assert item_content == expected

    clean_up(item_dir, item)

    item.set_filename("select multiple")
    item.set_description("select multiple")
    item.set_pref_label("select multiple")
    item.set_question("question for select item with multiple responses")
    response_options.set_multiple_choice(True)
    item.set_input_type_as_select(response_options)
    item.write(item_dir)

    item_content, expected = load_jsons(item_dir, item)
    assert item_content == expected

    clean_up(item_dir, item)


def test_slider():

    item = Item(name="slider", question="question for slider item")

    response_options = ResponseOption()
    response_options.add_choice("not at all", 0)
    response_options.add_choice("a bit", 1)
    response_options.add_choice("so so", 2)
    response_options.add_choice("a lot", 3)
    response_options.add_choice("very much", 4)
    response_options.set_max(4)

    item.set_input_type_as_slider(response_options)

    item.write(item_dir)
    item_content, expected = load_jsons(item_dir, item)
    assert item_content == expected

    clean_up(item_dir, item)


"""
Just to check that item with read only values

Tries to recreate the item from
reproschema/tests/data/activities/items/activity1_total_score
"""
my_path = Path(__file__).resolve().parent
reproschema_test_data = my_path.joinpath(my_path, "..", "..", "tests", "data")


def test_read_only():

    item = Item(name="activity1_total_score", ext="", input_type="int")
    item.at_context = "../../../contexts/generic"
    item.update()
    item.set_filename("activity1_total_score")
    item.schema["prefLabel"] = "activity1_total_score"
    item.set_description("Score item for Activity 1")
    item.set_read_only_value(True)
    item.response_options.set_max(3)
    item.response_options.set_min(0)
    item.unset(["question"])

    item.write(item_dir)

    output_file = os.path.join(item_dir, item.at_id)
    item_content = read_json(output_file)

    # test against one of the pre existing files
    data_file = os.path.join(
        reproschema_test_data, "activities", "items", "activity1_total_score"
    )
    expected = read_json(data_file)
    assert item_content == expected

    clean_up(item_dir, item)
