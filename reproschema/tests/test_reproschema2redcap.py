import os
import pytest
from click.testing import CliRunner
from ..cli import main
from shutil import copytree, rmtree
from pathlib import Path
import csv
import tempfile

def test_reproschema2redcap_success():
    runner = CliRunner()

    with runner.isolated_filesystem():
        # Create a temporary directory for output
        temp_dir = tempfile.mkdtemp(dir='.')
        print(f"Temporary directory: {temp_dir}")
        # Copy necessary test data into the isolated filesystem
        original_data_dir = os.path.join(
            os.path.dirname(__file__), "test_rs2redcap_data", "test_redcap2rs"
        )
        copytree(original_data_dir, "input_data")

        input_path = Path("input_data")  # Using Path object
        output_csv_path = os.path.join(temp_dir, "output.csv")

        # Invoke the reproschema2redcap command
        result = runner.invoke(
            main, ["reproschema2redcap", str(input_path), output_csv_path]
        )

        # Print the output for debugging
        print(result.output)

        # Assert the expected outcomes
        assert result.exit_code == 0

        # Check if the output CSV file has been created
        assert os.path.exists(output_csv_path)

        # Read and print the contents of the CSV file
        with open(output_csv_path, "r", encoding="utf-8") as csv_file:
            reader = csv.reader(csv_file)
            csv_contents = list(reader)
            print("CSV File Contents:")
            for row in csv_contents:
                print(row)

        # Optionally, assert conditions about the CSV contents
        # For example, assert that the file has more than just headers
        assert len(csv_contents) > 1  # More than one row indicates content beyond headers

        # Clean up temporary directory after use (optional)
        # rmtree(temp_dir)