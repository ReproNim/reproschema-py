import os
from pathlib import Path

import pytest
from utils import clean_up
from utils import load_jsons
from utils import output_dir
from utils import read_json

from reproschema.models.item import Item
from reproschema.models.item import ResponseOption

item_dir = output_dir("items")


def test_default():

    item = Item(name="default", output_dir=item_dir)
    print(item.schema_order)

    item.write()
    item_content, expected = load_jsons(item_dir, item)
    assert item_content == expected

    clean_up(item_dir, item)


@pytest.mark.parametrize(
    "name, question, input_type",
    [
        ("text", "question for text item", "text"),
        ("multitext", "item with several text field", "multitext"),
        ("email", "input email address", "email"),
        ("participant id", "input the participant id number", "pid"),
        ("date", "input a date", "date"),
        ("time range", "input a time range", "timeRange"),
        ("year", "input a year", "year"),
        ("language", "item to select several language", "selectLanguage"),
        ("country", "select a country", "selectCountry"),
        ("state", "select a USA state", "selectState"),
        ("float", "item to input a float", "float"),
        ("integer", "item to input a integer", "integer"),
    ],
)
def test_items(name, question, input_type):

    item = Item(
        name=name, question=question, input_type=input_type, output_dir=item_dir
    )

    item.write()
    item_content, expected = load_jsons(item_dir, item)
    assert item_content == expected

    clean_up(item_dir, item)


"""
NUMERICAL ITEMS
"""


"""
SELECTION ITEMS: radio and select
tested both with:
- only one response allowed
- multiple responses allowed
"""


def test_radio():

    response_options = ResponseOption(multipleChoice=False)
    response_options.add_choice(name="Not at all", value=0)
    response_options.add_choice(name="Several days", value=1)

    item = Item(name="radio", question="question for radio item", output_dir=item_dir)
    item.set_input_type_as_radio(response_options)

    item.write()
    item_content, expected = load_jsons(item_dir, item)
    assert item_content == expected

    clean_up(item_dir, item)

    item.set_filename("radio multiple")
    item.description = "radio multiple"
    item.update()
    item.set_pref_label("radio multiple")
    item.set_question("question for radio item with multiple responses")
    response_options.multipleChoice = True
    item.set_input_type_as_radio(response_options)
    item.write()

    item_content, expected = load_jsons(item_dir, item)
    assert item_content == expected

    clean_up(item_dir, item)


def test_select():

    response_options = ResponseOption(multipleChoice=False)
    response_options.add_choice(name="Response option 1", value=0)
    response_options.add_choice(name="Response option 2", value=1)
    response_options.add_choice(name="Response option 3", value=2)

    item = Item(name="select", question="question for select item", output_dir=item_dir)
    item.set_input_type_as_select(response_options)

    item.write()
    item_content, expected = load_jsons(item_dir, item)
    assert item_content == expected

    clean_up(item_dir, item)

    item.set_filename("select multiple")
    item.description = "select multiple"
    item.update()
    item.set_pref_label("select multiple")
    item.set_question("question for select item with multiple responses")
    response_options.multipleChoice = True
    item.set_input_type_as_select(response_options)
    item.write()

    item_content, expected = load_jsons(item_dir, item)
    assert item_content == expected

    clean_up(item_dir, item)


def test_slider():

    response_options = ResponseOption()
    response_options.add_choice(name="not at all", value=0)
    response_options.add_choice(name="a bit", value=1)
    response_options.add_choice(name="so so", value=2)
    response_options.add_choice(name="a lot", value=3)
    response_options.add_choice(name="very much", value=4)

    item = Item(name="slider", question="question for slider item", output_dir=item_dir)
    item.set_input_type_as_slider(response_options)

    item.write()
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

    item = Item(
        name="activity1_total_score",
        ext="",
        input_type="integer",
        read_only=True,
        output_dir=item_dir,
    )
    item.at_context = "../../../contexts/generic"
    item.description = "Score item for Activity 1"
    item.update()
    item.set_filename("activity1_total_score")
    item.set_pref_label("activity1_total_score")
    item.response_options.set_max(3)
    item.response_options.set_min(0)
    item.unset(["question"])

    item.write()

    output_file = os.path.join(item_dir, item.at_id)
    item_content = read_json(output_file)

    # test against one of the pre existing files
    data_file = os.path.join(
        reproschema_test_data, "activities", "items", "activity1_total_score"
    )
    expected = read_json(data_file)
    assert item_content == expected

    clean_up(item_dir, item)
