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
            os.path.dirname(__file__), "test_reproschema2fhir_data/activities"
        )
        copytree(original_data_dir, "input_data")

        input_path = Path("input_data")
        output_path = os.path.join(tmpdir)

        result = runner.invoke(
            main, ["reproschema2fhir", str(input_path), str(output_path)]
        )
        print("input", original_data_dir)
        print("output", output_path)

        assert result.exit_code == 0

        assert os.path.exists(output_path)
        assert len(os.listdir(output_path)) > 0

        # Clean up temporary directory after use (optional)
        # rmtree(tmpdir)
