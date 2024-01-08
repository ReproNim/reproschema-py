import os
import pytest
from click.testing import CliRunner
from ..cli import main
from shutil import copytree
from pathlib import Path
import csv


def test_reproschema2redcap_success():
    runner = CliRunner()

    with runner.isolated_filesystem():
        # Copy necessary test data into the isolated filesystem
        original_data_dir = os.path.join(
            os.path.dirname(__file__), "test_rs2redcap_data"
        )
        copytree(original_data_dir, "input_data")

        input_path = Path("input_data")  # Using Path object
        output_csv_path = "output.csv"

        # Invoke the reproschema2redcap command
        result = runner.invoke(
            main, ["reproschema2redcap", str(input_path), output_csv_path]
        )

        # Print the output for debugging
        print(result.output)

        # Assert the expected outcomes
        assert result.exit_code == 0
        assert (
            f"Converted reproschema JSON from {input_path} to Redcap CSV at {output_csv_path}"
            in result.output
        )

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
        # For example, assert that the file is not empty
        assert len(csv_contents) > 0
