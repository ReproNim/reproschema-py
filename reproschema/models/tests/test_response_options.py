from utils import clean_up
from utils import load_jsons
from utils import output_dir

from reproschema.models.response_options import Choice
from reproschema.models.response_options import ResponseOption


response_options_dir = output_dir("response_options")


def test_choice():
    choice = Choice(name="Not at all", value=1)
    assert choice.schema == {
        "name": {"en": "Not at all"},
        "value": 1,
    }


def test_example():

    response_options = ResponseOption(output_dir=response_options_dir)
    response_options.set_filename("example")
    response_options.set_valueType("integer")

    response_options.add_choice(name="Not at all", value=0)
    for i in range(1, 5):
        response_options.add_choice(value=i)
    response_options.add_choice(name="Completely", value=6)

    print(response_options.schema)

    response_options.write()
    content, expected = load_jsons(response_options_dir, response_options)
    assert content == expected

    clean_up(response_options_dir, response_options)


def test_default():

    response_options = ResponseOption(output_dir=response_options_dir)
    response_options.set_defaults()

    response_options.write()
    content, expected = load_jsons(response_options_dir, response_options)
    assert content == expected

    clean_up(response_options_dir, response_options)
