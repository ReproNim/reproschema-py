"""
Tests for nbdc2reproschema converter.

Tests support both Parquet (preferred) and legacy RDS formats.
"""

import os
import shutil
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from ..cli import main
from ..nbdc2reproschema import detect_input_format, load_nbdc_data_csv

YAML_FILE_NAME = "abcd.yml"
YAML_TEST_FILE = os.path.join(
    os.path.dirname(__file__), "..", "example", "nbdc", YAML_FILE_NAME
)


class TestFormatDetection:
    """Tests for input format detection."""

    def test_detect_parquet_format(self):
        """Test detection of Parquet format."""
        assert detect_input_format(Path("data.parquet")) == "parquet"
        assert detect_input_format(Path("data.PARQUET")) == "parquet"

    def test_detect_csv_format(self):
        """Test detection of CSV format."""
        assert detect_input_format(Path("data.csv")) == "csv"
        assert detect_input_format(Path("data.CSV")) == "csv"

    def test_detect_rds_format(self):
        """Test detection of RDS format."""
        assert detect_input_format(Path("data.rds")) == "rds"
        assert detect_input_format(Path("data.RDS")) == "rds"

    def test_detect_unknown_format_defaults_to_csv(self):
        """Test that unknown extensions default to CSV."""
        assert detect_input_format(Path("data.txt")) == "csv"
        assert detect_input_format(Path("data.unknown")) == "csv"

    def test_detect_format_no_extension(self):
        """Test that files without extension default to CSV."""
        assert detect_input_format(Path("data")) == "csv"


class TestLoadFunctions:
    """Tests for data loading functions."""

    def test_load_csv(self, tmpdir):
        """Test loading CSV data."""
        import pandas as pd

        # Create test CSV file
        test_file = tmpdir.join("test.csv")
        df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        df.to_csv(test_file, index=False)

        # Load and verify
        loaded_df = load_nbdc_data_csv(Path(str(test_file)))
        assert len(loaded_df) == 3
        assert list(loaded_df.columns) == ["a", "b"]


class TestCLI:
    """Tests for CLI interface."""

    def test_yaml_config_exists(self):
        """Test that the YAML config file exists."""
        assert os.path.exists(
            YAML_TEST_FILE
        ), f"YAML config file not found: {YAML_TEST_FILE}"

        with open(YAML_TEST_FILE, "r") as f:
            config = yaml.safe_load(f)

        assert "protocol_name" in config
        assert config["protocol_name"] == "ABCD"
        assert config.get("version") == "6.0"

    def test_nbdc2reproschema_missing_input_file(self, tmpdir):
        """Test handling of missing input file."""
        runner = CliRunner()

        temp_yaml_file = tmpdir.join(YAML_FILE_NAME)
        shutil.copy(YAML_TEST_FILE, str(temp_yaml_file))

        with tmpdir.as_cwd():
            result = runner.invoke(
                main,
                [
                    "nbdc2reproschema",
                    "nonexistent.parquet",
                    str(temp_yaml_file),
                ],
            )

            # Should fail with missing input file
            assert result.exit_code != 0
            assert "does not exist" in result.output.lower()

    def test_nbdc2reproschema_missing_yaml(self, tmpdir):
        """Test handling of missing configuration file."""
        runner = CliRunner()

        # Create a dummy input file first
        import pandas as pd

        input_file = tmpdir.join("dummy.parquet")
        df = pd.DataFrame({"a": [1]})
        df.to_parquet(str(input_file))

        with tmpdir.as_cwd():
            result = runner.invoke(
                main,
                [
                    "nbdc2reproschema",
                    str(input_file),
                    "nonexistent_config.yml",
                ],
            )

            # Should fail with missing config file
            assert result.exit_code != 0
            assert "does not exist" in result.output.lower()

    def test_nbdc2reproschema_with_csv_fixture(self, tmpdir):
        """Test nbdc2reproschema with a minimal CSV fixture."""
        import pandas as pd

        runner = CliRunner()

        # Create minimal test data matching NBDC structure
        test_data = pd.DataFrame(
            {
                "name": ["item1", "item2"],
                "table_name": ["activity1", "activity1"],
                "label": ["Question 1", "Question 2"],
                "type_var": ["text", "text"],
                "data_type": ["string", "string"],
                "instruction": ["", ""],
            }
        )

        input_file = tmpdir.join("test_data.csv")
        test_data.to_csv(input_file, index=False)

        # Create minimal YAML config
        yaml_content = {
            "protocol_name": "Test_Protocol",
            "protocol_display_name": "Test Protocol",
        }
        temp_yaml_file = tmpdir.join("test_config.yml")
        with open(str(temp_yaml_file), "w") as f:
            yaml.dump(yaml_content, f)

        with tmpdir.as_cwd():
            result = runner.invoke(
                main,
                [
                    "nbdc2reproschema",
                    str(input_file),
                    str(temp_yaml_file),
                ],
            )

            print("Command output:", result.output)

            assert (
                result.exit_code == 0
            ), f"Command failed with: {result.output}"
            assert os.path.isdir(
                "Test_Protocol"
            ), "Expected output directory 'Test_Protocol' does not exist"


class TestIntegration:
    """Integration tests that require R and NBDCtoolsData."""

    def test_nbdc2reproschema_with_parquet(self, tmpdir):
        """Test nbdc2reproschema with Parquet input (requires R-generated fixture)."""
        pytest.skip(
            "Skip: Requires R-generated Parquet fixture - test manually"
        )

        # This test would use a Parquet file generated by:
        # Rscript scripts/export_nbdc_parquet.R abcd 6.0
        pass

    def test_nbdc2reproschema_with_rds(self, tmpdir):
        """Test nbdc2reproschema with a pre-exported RDS file."""
        pytest.skip("Skip: Requires pre-exported RDS file - test manually")

        # Create a small test RDS file first
        # This test would use a pre-exported RDS file
        pass


class TestHBCD:
    """Tests specific to HBCD data conversion."""

    def test_hbcd_config_exists(self):
        """Test that HBCD config file exists."""
        hbcd_yaml = os.path.join(
            os.path.dirname(__file__), "..", "example", "nbdc", "hbcd.yml"
        )
        assert os.path.exists(hbcd_yaml), f"HBCD config file not found: {hbcd_yaml}"

    def test_summary_score_type_mapping(self):
        """Test that 'summary score' type_var maps correctly to number."""
        from ..nbdc_mappings import get_nbdc_input_type

        assert get_nbdc_input_type("summary score") == "number"

    def test_derived_item_type_mapping(self):
        """Test that 'derived item' type_var maps correctly to number."""
        from ..nbdc_mappings import get_nbdc_input_type

        assert get_nbdc_input_type("derived item") == "number"

    def test_hbcd_with_csv_fixture(self, tmpdir):
        """Test nbdc2reproschema with HBCD-like CSV data."""
        import pandas as pd

        runner = CliRunner()

        # Create test data matching HBCD structure (with summary score)
        test_data = pd.DataFrame({
            "name": ["item1", "item2", "item3"],
            "table_name": ["activity1", "activity1", "activity1"],
            "label": ["Question 1", "Question 2", "Score"],
            "type_var": ["item", "administrative", "summary score"],  # HBCD types
            "data_type": ["string", "string", "integer"],
            "instruction": ["", "", ""],
        })

        input_file = tmpdir.join("hbcd_test_data.csv")
        test_data.to_csv(input_file, index=False)

        # Create HBCD YAML config
        yaml_content = {
            "protocol_name": "HBCD_Test",
            "protocol_display_name": "HBCD Test Protocol",
        }
        temp_yaml_file = tmpdir.join("hbcd_test_config.yml")
        with open(str(temp_yaml_file), "w") as f:
            yaml.dump(yaml_content, f)

        with tmpdir.as_cwd():
            result = runner.invoke(
                main,
                [
                    "nbdc2reproschema",
                    str(input_file),
                    str(temp_yaml_file),
                ],
            )

            assert result.exit_code == 0, f"Command failed with: {result.output}"
            assert os.path.isdir("HBCD_Test")
