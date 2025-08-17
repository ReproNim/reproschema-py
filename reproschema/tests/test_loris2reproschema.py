import os
import shutil

import yaml
from click.testing import CliRunner

from ..cli import main

CSV_FILE_NAME = "HBCD_LORIS.csv"
YAML_FILE_NAME = "hbcd-loris.yml"
CSV_TEST_FILE = os.path.join(
    os.path.dirname(__file__), "..", "example", "loris", CSV_FILE_NAME
)
YAML_TEST_FILE = os.path.join(
    os.path.dirname(__file__), "..", "example", "loris", YAML_FILE_NAME
)


def test_loris2reproschema(tmpdir):
    runner = CliRunner()

    temp_csv_file = tmpdir.join(CSV_FILE_NAME)
    temp_yaml_file = tmpdir.join(YAML_FILE_NAME)

    shutil.copy(CSV_TEST_FILE, str(temp_csv_file))

    shutil.copy(YAML_TEST_FILE, str(temp_yaml_file))

    with tmpdir.as_cwd():
        # Read YAML to find the expected output directory name
        with open(str(temp_yaml_file), "r") as file:
            protocol = yaml.safe_load(file)
        protocol_name = protocol.get("protocol_name", "").replace(" ", "_")

        result = runner.invoke(
            main,
            [
                "loris2reproschema",
                str(temp_csv_file),
                str(temp_yaml_file),
            ],
        )

        print("Command output:", result.output)  # Add debug output

        assert result.exit_code == 0, f"Command failed with: {result.output}"
        assert os.path.isdir(
            protocol_name
        ), f"Expected output directory '{protocol_name}' does not exist"


def test_loris2reproschema_missing_config(tmpdir):
    """Test handling of missing configuration file"""
    runner = CliRunner()
    
    temp_csv_file = tmpdir.join(CSV_FILE_NAME)
    shutil.copy(CSV_TEST_FILE, str(temp_csv_file))
    
    with tmpdir.as_cwd():
        result = runner.invoke(
            main,
            [
                "loris2reproschema",
                str(temp_csv_file),
                "nonexistent_config.yml",
            ],
        )
        
        # Should fail with missing config file
        assert result.exit_code != 0
        assert "does not exist" in result.output.lower()
