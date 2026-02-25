"""
Tests for odc2reproschema converter.
"""

import json
import os
from pathlib import Path

from click.testing import CliRunner

from ..cli import main
from ..odc_mappings import get_odc_input_type, get_odc_value_type


class TestTypeMappings:
    """Tests for field type mappings."""

    def test_input_type_mapping(self):
        assert get_odc_input_type("string", "input") == "text"
        assert get_odc_input_type("string", "textarea") == "text"
        assert get_odc_input_type("number", "input") == "number"
        assert get_odc_input_type("number", "slider") == "slider"
        assert get_odc_input_type("boolean", "checkbox") == "checkbox"
        assert get_odc_input_type("date") == "date"
        assert get_odc_input_type("set", "select") == "select"

    def test_value_type_mapping(self):
        assert get_odc_value_type("string") == "xsd:string"
        assert get_odc_value_type("number") == "xsd:decimal"
        assert get_odc_value_type("boolean") == "xsd:boolean"
        assert get_odc_value_type("date") == "xsd:date"


class TestCLI:
    """Tests for CLI interface."""

    def test_odc2reproschema_with_fixture(self, tmpdir):
        runner = CliRunner()

        # Create minimal test data matching ODC structure
        test_data = {
            "__runtimeVersion": 1,
            "kind": "FORM",
            "internal": {"name": "test_instrument", "edition": 1},
            "details": {"title": "Test Instrument"},
            "content": {
                "item1": {
                    "kind": "string",
                    "variant": "input",
                    "label": "Question 1",
                },
                "item2": {
                    "kind": "number",
                    "variant": "input",
                    "label": "Question 2",
                },
                "likert1": {
                    "kind": "number-record",
                    "variant": "likert",
                    "label": "Likert Group",
                    "items": {"q1": {"label": "Sub-question 1"}},
                    "options": {"1": "Option 1", "2": "Option 2"},
                },
            },
        }

        input_file = tmpdir.join("test_odc.json")
        with open(str(input_file), "w") as f:
            json.dump(test_data, f)

        with tmpdir.as_cwd():
            result = runner.invoke(
                main,
                [
                    "odc2reproschema",
                    str(input_file),
                ],
            )

            assert (
                result.exit_code == 0
            ), f"Command failed with: {result.output}"
            assert os.path.isdir(
                "test_instrument"
            ), "Expected output directory 'test_instrument' does not exist"
            # Activity schema is created at activities/{name}/{name}_schema (no .jsonld extension)
            assert os.path.exists(
                "test_instrument/activities/test_instrument/test_instrument_schema"
            ), "Expected activity schema at activities/test_instrument/test_instrument_schema"
            # Items are created at activities/{name}/items/{item_id} (no .jsonld extension)
            assert os.path.exists(
                "test_instrument/activities/test_instrument/items/item1"
            ), "Expected item at activities/test_instrument/items/item1"
            assert os.path.exists(
                "test_instrument/activities/test_instrument/items/likert1_q1"
            ), "Expected likert item at activities/test_instrument/items/likert1_q1"
            # Protocol schema is created at {name}/{name}_schema (no .jsonld extension)
            assert os.path.exists(
                "test_instrument/test_instrument/test_instrument_schema"
            ), "Expected protocol schema at test_instrument/test_instrument/test_instrument_schema"
