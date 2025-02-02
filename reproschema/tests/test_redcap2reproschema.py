import os
import shutil

import pytest
import yaml
from click.testing import CliRunner
from ..redcap2reproschema import process_field_properties

from ..cli import main

CSV_FILE_NAME = "redcap_dict.csv"
YAML_FILE_NAME = "redcap2rs.yaml"
CSV_TEST_FILE = os.path.join(
    os.path.dirname(__file__), "test_redcap2rs_data", CSV_FILE_NAME
)
YAML_TEST_FILE = os.path.join(
    os.path.dirname(__file__), "test_redcap2rs_data", YAML_FILE_NAME
)


def test_redcap2reproschema(tmpdir):
    runner = CliRunner()

    temp_csv_file = tmpdir.join(CSV_FILE_NAME)
    temp_yaml_file = tmpdir.join(YAML_FILE_NAME)

    shutil.copy(CSV_TEST_FILE, str(temp_csv_file))
    shutil.copy(YAML_TEST_FILE, str(temp_yaml_file))

    # Add debug output to see the content of the CSV file
    with open(str(temp_csv_file), "r") as f:
        print("CSV content:", f.read())

    with tmpdir.as_cwd():
        # Read YAML to find the expected output directory name
        with open(str(temp_yaml_file), "r") as file:
            protocol = yaml.safe_load(file)
        protocol_name = protocol.get("protocol_name", "").replace(" ", "_")

        result = runner.invoke(
            main,
            [
                "redcap2reproschema",
                str(temp_csv_file),
                str(temp_yaml_file),
            ],
        )

        print("Command output:", result.output)  # Add debug output

        assert result.exit_code == 0, f"Command failed with: {result.output}"
        assert os.path.isdir(
            protocol_name
        ), f"Expected output directory '{protocol_name}' does not exist"

def test_process_field_properties_visibility():
    # Test case 1: No branching logic or annotations
    field_data = {
        "Variable / Field Name": "test_field"
    }
    result = process_field_properties(field_data)
    assert "isVis" not in result

    # Test case 2: With branching logic
    field_data = {
        "Variable / Field Name": "test_field",
        "Branching Logic (Show field only if...)": "[age] > 18"
    }
    result = process_field_properties(field_data)
    assert result["isVis"] == "age > 18"

    # Test case 3: With @HIDDEN annotation
    field_data = {
        "Variable / Field Name": "test_field", 
        "Field Annotation": "@HIDDEN"
    }
    result = process_field_properties(field_data)
    assert result["isVis"] is False

    # Test case 4: With both branching logic and @HIDDEN
    field_data = {
        "Variable / Field Name": "test_field",
        "Branching Logic (Show field only if...)": "[age] > 18",
        "Field Annotation": "@HIDDEN"
    }
    result = process_field_properties(field_data)
    assert result["isVis"] is False