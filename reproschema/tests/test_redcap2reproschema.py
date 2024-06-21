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


def test_redcap2reproschema(tmpdir):
    runner = CliRunner()

    temp_csv_file = tmpdir.join(CSV_FILE_NAME)
    temp_yaml_file = tmpdir.join(YAML_FILE_NAME)

    shutil.copy(CSV_TEST_FILE, str(temp_csv_file))  # Convert to string
    shutil.copy(YAML_TEST_FILE, str(temp_yaml_file))  # Convert to string
    print("tmpdir: ", tmpdir)
    # Change the current working directory to tmpdir
    with tmpdir.as_cwd():
        # Read YAML to find the expected output directory name
        with open(str(temp_yaml_file), "r") as file:  # Convert to string
            protocol = yaml.safe_load(file)
        protocol_name = protocol.get("protocol_name", "").replace(" ", "_")

        result = runner.invoke(
            main,
            [
                "redcap2reproschema",
                str(temp_csv_file),
                str(temp_yaml_file),
            ],  # Convert to string
        )

        assert (
            result.exit_code == 0
        ), f"The command failed to execute successfully: {result.output}"
        assert os.path.isdir(
            protocol_name
        ), f"Expected output directory '{protocol_name}' does not exist"
