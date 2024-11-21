import os
import shutil

import pytest
import yaml
from click.testing import CliRunner

from ..cli import main
from ..redcap2reproschema import process_choices


def test_process_choices_numeric_codes():
    # Test standard numeric codes with descriptions
    choices_str = "1, Male    | 2, Female | 3, Other"
    choices, value_types = process_choices(choices_str, "gender")
    assert choices == [
        {"name": {"en": "Male"}, "value": 1},
        {"name": {"en": "Female"}, "value": 2},
        {"name": {"en": "Other"}, "value": 3},
    ]
    assert value_types == ["xsd:integer"]


def test_process_choices_boolean():
    # Test boolean choices (Yes/No)
    choices_str = "1, Yes | 0, No"
    choices, value_types = process_choices(choices_str, "boolean_field")
    assert choices == [
        {"name": {"en": "Yes"}, "value": 1},
        {"name": {"en": "No"}, "value": 0},
    ]
    assert value_types == ["xsd:integer"]


def test_process_choices_special_characters():
    # Test choices with special characters
    choices_str = "1, Option A | 2, \"Option B\" | 3, Option C with 'quotes'"
    choices, value_types = process_choices(choices_str, "special_chars")
    assert choices == [
        {"name": {"en": "Option A"}, "value": 1},
        {"name": {"en": '"Option B"'}, "value": 2},
        {"name": {"en": "Option C with 'quotes'"}, "value": 3},
    ]
    assert value_types == ["xsd:integer"]


def test_process_choices_with_missing_values():
    # Test choices with a missing value (commonly used for "Not applicable" or "Prefer not to say")
    choices_str = "1, Yes | 2, No | 99, Not applicable"
    choices, value_types = process_choices(choices_str, "missing_values")
    assert choices == [
        {"name": {"en": "Yes"}, "value": 1},
        {"name": {"en": "No"}, "value": 2},
        {"name": {"en": "Not applicable"}, "value": 99},
    ]
    assert value_types == ["xsd:integer"]


def test_process_choices_with_unicode():
    # Test choices with Unicode characters (e.g., accents, symbols)
    choices_str = "1, Café | 2, Niño | 3, Résumé | 4, ☺"
    choices, value_types = process_choices(choices_str, "unicode_field")
    assert choices == [
        {"name": {"en": "Café"}, "value": 1},
        {"name": {"en": "Niño"}, "value": 2},
        {"name": {"en": "Résumé"}, "value": 3},
        {"name": {"en": "☺"}, "value": 4},
    ]
    assert value_types == ["xsd:integer"]


def test_process_choices_alpha_codes():
    # Test alpha codes (e.g., categorical text codes)
    choices_str = "A, Apple | B, Banana | C, Cherry"
    choices, value_types = process_choices(choices_str, "alpha_codes")
    assert choices == [
        {"name": {"en": "Apple"}, "value": "A"},
        {"name": {"en": "Banana"}, "value": "B"},
        {"name": {"en": "Cherry"}, "value": "C"},
    ]
    assert sorted(value_types) == ["xsd:string"]


def test_process_choices_incomplete_values():
    # Test choices with missing descriptions
    choices_str = "1, Yes | 2, | 3, No"
    choices, value_types = process_choices(choices_str, "incomplete_values")
    assert choices == [
        {"name": {"en": "Yes"}, "value": 1},
        {"name": {"en": ""}, "value": 2},
        {"name": {"en": "No"}, "value": 3},
    ]
    assert value_types == ["xsd:integer"]


def test_process_choices_numeric_strings():
    # Test numeric strings as values (e.g., not converted to integers)
    choices_str = "001, Option 001 | 002, Option 002 | 003, Option 003"
    choices, value_types = process_choices(choices_str, "numeric_strings")
    assert choices == [
        {"name": {"en": "Option 001"}, "value": "001"},
        {"name": {"en": "Option 002"}, "value": "002"},
        {"name": {"en": "Option 003"}, "value": "003"},
    ]
    assert sorted(value_types) == ["xsd:string"]


def test_process_choices_spaces_in_values():
    # Test choices with spaces in values and names
    choices_str = "A B, Choice AB | C D, Choice CD"
    choices, value_types = process_choices(choices_str, "spaces_in_values")
    assert choices == [
        {"name": {"en": "Choice AB"}, "value": "A B"},
        {"name": {"en": "Choice CD"}, "value": "C D"},
    ]
    assert sorted(value_types) == ["xsd:string"]


# Run pytest if script is called directly
if __name__ == "__main__":
    pytest.main()
