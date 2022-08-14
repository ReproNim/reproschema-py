from utils import clean_up
from utils import load_jsons
from utils import output_dir

from reproschema.models.item import ResponseOption

response_options_dir = output_dir("response_options")


def test_example():

    response_options = ResponseOption(output_dir=response_options_dir)
    response_options.set_defaults()
    response_options.set_filename("example")
    response_options.set_type("integer")
    response_options.unset("multipleChoice")
    response_options.add_choice("Not at all", 0)
    for i in range(1, 5):
        response_options.add_choice("", i)
    response_options.add_choice("Completely", 6)

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
