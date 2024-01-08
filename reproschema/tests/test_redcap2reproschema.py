import os
import shutil
import pytest
from click.testing import CliRunner
from ..cli import main  # Import the Click group

# Assuming your test files are located in a 'tests' directory
CSV_FILE_NAME = "redcap_dict.csv"
YAML_FILE_NAME = "redcap2rs.yaml"
CSV_TEST_FILE = os.path.join(os.path.dirname(__file__), "test_data", CSV_FILE_NAME)
YAML_TEST_FILE = os.path.join(os.path.dirname(__file__), "test_data", YAML_FILE_NAME)


def test_redcap2reproschema_success():
    runner = CliRunner()

    with runner.isolated_filesystem():
        # Copy the test files to the isolated filesystem
        shutil.copy(CSV_TEST_FILE, CSV_FILE_NAME)
        shutil.copy(YAML_TEST_FILE, YAML_FILE_NAME)

        # Run the command within the isolated filesystem
        result = runner.invoke(
            main, ["redcap2reproschema", CSV_FILE_NAME, YAML_FILE_NAME]
        )
        print(result.output)
        assert result.exit_code == 0
