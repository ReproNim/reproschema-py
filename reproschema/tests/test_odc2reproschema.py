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


class TestComprehensiveInstrument:
    """Tests using the comprehensive sample ODC instrument fixture."""

    @property
    def fixture_path(self) -> Path:
        """Return path to the comprehensive sample instrument fixture."""
        return Path(__file__).parent.parent.parent / "tests" / "fixtures" / "sample_odc_instrument.json"

    def test_comprehensive_instrument_conversion(self, tmpdir):
        """Test conversion of comprehensive instrument with all field types."""
        runner = CliRunner()

        with tmpdir.as_cwd():
            result = runner.invoke(
                main,
                [
                    "odc2reproschema",
                    str(self.fixture_path),
                ],
            )

            assert result.exit_code == 0, f"Command failed with: {result.output}"

            # Verify output directory structure
            assert os.path.isdir("sample_clinical_assessment"), "Expected output directory"
            activity_dir = "sample_clinical_assessment/activities/sample_clinical_assessment"
            items_dir = f"{activity_dir}/items"

            # Verify all field types are converted
            expected_items = {
                # string/input -> text
                "patient_name": {"input_type": "text", "value_type": "xsd:string"},
                # string/textarea -> text
                "notes": {"input_type": "text", "value_type": "xsd:string"},
                # number/input -> number
                "age": {"input_type": "number", "value_type": "xsd:decimal", "has_min_max": True},
                # number/slider -> slider with min/max
                "pain_level": {"input_type": "slider", "value_type": "xsd:decimal", "has_min_max": True},
                # boolean/checkbox -> checkbox
                "consent": {"input_type": "checkbox", "value_type": "xsd:boolean"},
                # date -> date
                "assessment_date": {"input_type": "date", "value_type": "xsd:date"},
                # string/radio -> radio with choices
                "gender": {"input_type": "radio", "has_choices": True},
                # string/select -> select with choices
                "medication_frequency": {"input_type": "select", "has_choices": True},
                # set/listbox -> select with multipleChoice
                "symptoms": {"input_type": "select", "has_multiple_choice": True, "has_choices": True},
                # number-record/likert -> multiple radio items
                "satisfaction_likert_overall": {"input_type": "radio", "has_choices": True, "value_type": "xsd:integer"},
                "satisfaction_likert_wait_time": {"input_type": "radio", "has_choices": True, "value_type": "xsd:integer"},
                "satisfaction_likert_staff_helpfulness": {"input_type": "radio", "has_choices": True, "value_type": "xsd:integer"},
                # record-array -> prefixed sub-items
                "medical_history_condition": {"input_type": "text", "value_type": "xsd:string"},
                "medical_history_year_diagnosed": {"input_type": "number", "value_type": "xsd:decimal"},
                "medical_history_treated": {"input_type": "checkbox", "value_type": "xsd:boolean"},
            }

            for item_name, expected_props in expected_items.items():
                item_path = f"{items_dir}/{item_name}"
                assert os.path.exists(item_path), f"Expected item at {item_path}"

                with open(item_path) as f:
                    item_data = json.load(f)

                # Verify input type
                if "input_type" in expected_props:
                    assert item_data["ui"]["inputType"] == expected_props["input_type"], \
                        f"Item {item_name} has wrong inputType"

                # Verify value type
                if "value_type" in expected_props:
                    assert item_data["responseOptions"]["valueType"][0] == expected_props["value_type"], \
                        f"Item {item_name} has wrong valueType"

                # Verify min/max for numeric fields
                if expected_props.get("has_min_max"):
                    assert "minValue" in item_data["responseOptions"], \
                        f"Item {item_name} missing minValue"
                    assert "maxValue" in item_data["responseOptions"], \
                        f"Item {item_name} missing maxValue"

                # Verify choices for select/radio fields
                if expected_props.get("has_choices"):
                    assert "choices" in item_data["responseOptions"], \
                        f"Item {item_name} missing choices"
                    assert len(item_data["responseOptions"]["choices"]) > 0, \
                        f"Item {item_name} has empty choices"

                # Verify multipleChoice for set/listbox
                if expected_props.get("has_multiple_choice"):
                    assert item_data["responseOptions"].get("multipleChoice") is True, \
                        f"Item {item_name} missing multipleChoice=true"

    def test_activity_schema_order_and_properties(self, tmpdir):
        """Test that activity schema has correct order and addProperties."""
        runner = CliRunner()

        with tmpdir.as_cwd():
            result = runner.invoke(
                main,
                [
                    "odc2reproschema",
                    str(self.fixture_path),
                ],
            )

            assert result.exit_code == 0, f"Command failed with: {result.output}"

            activity_schema_path = "sample_clinical_assessment/activities/sample_clinical_assessment/sample_clinical_assessment_schema"
            with open(activity_schema_path) as f:
                activity_data = json.load(f)

            # Verify order array
            assert "ui" in activity_data
            assert "order" in activity_data["ui"]
            order = activity_data["ui"]["order"]

            # Expected order (matching the original content order)
            expected_order = [
                "items/patient_name",
                "items/notes",
                "items/age",
                "items/pain_level",
                "items/consent",
                "items/assessment_date",
                "items/gender",
                "items/symptoms",
                "items/medication_frequency",
                "items/satisfaction_likert_overall",
                "items/satisfaction_likert_wait_time",
                "items/satisfaction_likert_staff_helpfulness",
                "items/medical_history_condition",
                "items/medical_history_year_diagnosed",
                "items/medical_history_treated",
            ]

            assert order == expected_order, f"Order mismatch: {order}"

            # Verify addProperties
            assert "addProperties" in activity_data["ui"]
            add_properties = activity_data["ui"]["addProperties"]

            # Should have same number of properties as order items
            assert len(add_properties) == len(expected_order), \
                f"addProperties count ({len(add_properties)}) doesn't match order count ({len(expected_order)})"

            # Verify each addProperty has required fields
            for prop in add_properties:
                assert "isAbout" in prop, "addProperty missing isAbout"
                assert "isVis" in prop, "addProperty missing isVis"
                assert "variableName" in prop, "addProperty missing variableName"
                assert prop["isVis"] is True, "addProperty isVis should be True"

            # Verify variable names match expected items
            variable_names = [p["variableName"] for p in add_properties]
            expected_var_names = [
                "patient_name", "notes", "age", "pain_level", "consent",
                "assessment_date", "gender", "symptoms", "medication_frequency",
                "satisfaction_likert_overall", "satisfaction_likert_wait_time",
                "satisfaction_likert_staff_helpfulness",
                "medical_history_condition", "medical_history_year_diagnosed",
                "medical_history_treated"
            ]
            assert variable_names == expected_var_names, f"variableName mismatch: {variable_names}"
