import os
import shutil
import pytest
import yaml
from click.testing import CliRunner
from ..cli import main 

CSV_FILE_NAME = "redcap_dict.csv"
YAML_FILE_NAME = "redcap2rs.yaml"
CSV_TEST_FILE = os.path.join(
    os.path.dirname(__file__), "test_redcap2rs_data", CSV_FILE_NAME
)
YAML_TEST_FILE = os.path.join(
    os.path.dirname(__file__), "test_redcap2rs_data", YAML_FILE_NAME
)

def test_redcap2reproschema_success(tmpdir):
    runner = CliRunner()

    # Copy the test files to the custom temporary directory
    shutil.copy(CSV_TEST_FILE, tmpdir.join(CSV_FILE_NAME))
    shutil.copy(YAML_TEST_FILE, tmpdir.join(YAML_FILE_NAME))

    # Set the working directory to tmpdir
    with tmpdir.as_cwd():
        # Read YAML to find the expected output directory name
        with open(YAML_FILE_NAME, 'r') as file:
            protocol = yaml.safe_load(file)
        protocol_name = protocol.get("protocol_name", "").replace(" ", "_")

        result = runner.invoke(
            main, ["redcap2reproschema", CSV_FILE_NAME, YAML_FILE_NAME]
        )

        # Assertions
        assert result.exit_code == 0
        assert os.path.isdir(protocol_name), f"Expected output directory '{protocol_name}' does not exist"
