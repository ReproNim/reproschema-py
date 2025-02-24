import csv
import os
from pathlib import Path
from shutil import copytree, rmtree

import pytest
from click.testing import CliRunner

from ..cli import main


def test_reproschemaui2redcap(tmpdir):
    runner = CliRunner()

    with runner.isolated_filesystem():
        # Copy necessary test data into the isolated filesystem
        original_data_dir = os.path.join(
            os.path.dirname(__file__), "test_output2redcap"
        )
        copytree(original_data_dir, "input_data")

        input_path = Path("input_data")
        output_csv_path = os.path.join(tmpdir)

        result = runner.invoke(
            main,
            [
                "output2redcap",
                str(input_path),
                str(output_csv_path),
            ],
        )
        print("input", original_data_dir)
        print("output", output_csv_path)

        assert result.exit_code == 0

        assert os.path.exists(output_csv_path)
        output_file = os.path.join(output_csv_path, "redcap.csv")
        assert os.path.exists(output_file)

        with open(output_file, "r", encoding="utf-8") as csv_file:
            reader = csv.reader(csv_file)
            csv_contents = list(reader)

        assert (
            len(csv_contents) > 1
        )  # More than one row indicates content beyond headers

        # Clean up temporary directory after use (optional)
        # rmtree(tmpdir)
