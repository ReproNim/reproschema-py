"""
Convert NBDC data dictionary to ReproSchema format.

This module handles conversion of NBDC (Neurodata Without Borders/Data Coordinating Center)
study data from various formats (Parquet, CSV, RDS) to ReproSchema JSON-LD.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import pandas as pd
import yaml

from .context_url import CONTEXTFILE_URL
from .convertutils import (
    create_activity_schema,
    create_protocol_schema,
    parse_html,
)
from .nbdc_mappings import (
    NBDC_ADDITIONAL_NOTES_COLUMNS,
    NBDC_COLUMN_MAP,
    NBDC_COLUMN_REQUIRED,
    get_nbdc_input_type,
    get_nbdc_value_type,
    is_compute_field,
    is_readonly_field,
)

logger = logging.getLogger(__name__)


def read_nbdc_config(config_file: Path) -> Dict[str, Any]:
    """
    Read and validate the NBDC YAML configuration file.

    Args:
        config_file: Path to the YAML configuration file

    Returns:
        Dictionary containing the configuration

    Raises:
        FileNotFoundError: If the config file doesn't exist
        ValueError: If the YAML is invalid or missing required fields
        yaml.YAMLError: If the config file has invalid YAML syntax
    """
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            # Validate required fields
            required_fields = ["protocol_name"]
            missing = [
                field for field in required_fields if field not in config
            ]
            if missing:
                raise ValueError(
                    f"Missing required fields in config: {', '.join(missing)}"
                )
            return config
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file not found: {config_file}")
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in configuration file: {str(e)}")


def detect_input_format(file_path: Path) -> str:
    """Detect input format from file extension.

    Args:
        file_path: Path to the input file

    Returns:
        Format string: "parquet", "csv", or "rds"
    """
    ext = file_path.suffix.lower()
    format_map = {
        ".parquet": "parquet",
        ".csv": "csv",
        ".rds": "rds",
    }
    return format_map.get(ext, "csv")


def load_nbdc_data_parquet(file_path: Path) -> pd.DataFrame:
    """Load NBDC data from Parquet file.

    Args:
        file_path: Path to the Parquet file

    Returns:
        DataFrame containing the NBDC data dictionary

    Raises:
        ImportError: If pyarrow is not installed
    """
    try:
        import pyarrow.parquet  # noqa: F401
    except ImportError:
        raise ImportError(
            "pyarrow is required to read Parquet files. "
            "Install it with: pip install pyarrow"
        )
    return pd.read_parquet(file_path)


def load_nbdc_data_csv(file_path: Path) -> pd.DataFrame:
    """Load NBDC data from CSV file.

    Args:
        file_path: Path to the CSV file

    Returns:
        DataFrame containing the NBDC data dictionary
    """
    return pd.read_csv(file_path)


def load_nbdc_data_rds(rds_path: Path) -> pd.DataFrame:
    """
    Load NBDC data from RDS file using pyreadr.

    Args:
        rds_path: Path to the RDS file

    Returns:
        DataFrame containing the NBDC data dictionary
    """
    try:
        import pyreadr
    except ImportError:
        raise ImportError(
            "pyreadr is required to read RDS files. "
            "Install it with: pip install pyreadr"
        )

    result = pyreadr.read_r(str(rds_path))
    if len(result) != 1:
        raise ValueError(
            f"Expected single object in RDS file, got {len(result)}"
        )

    df = result[list(result.keys())[0]]
    return df


def load_nbdc_data(file_path: Path, input_format: str = None) -> pd.DataFrame:
    """Load NBDC data from file (auto-detect format).

    Args:
        file_path: Path to the input file
        input_format: Format hint ("parquet", "csv", "rds").
                     If None, format is auto-detected from file extension.

    Returns:
        DataFrame containing the NBDC data dictionary

    Raises:
        ValueError: If the format is not supported
    """
    if input_format is None:
        input_format = detect_input_format(file_path)

    loaders = {
        "parquet": load_nbdc_data_parquet,
        "csv": load_nbdc_data_csv,
        "rds": load_nbdc_data_rds,
    }

    if input_format not in loaders:
        raise ValueError(f"Unsupported format: {input_format}")

    return loaders[input_format](file_path)


def process_row(
    row: Dict[str, Any], activity_label: str
) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    """
    Process a single row of NBDC data and return structured data for an item.

    Args:
        row: Dictionary containing all fields from the NBDC data row
               Note: Columns should already be mapped using NBDC_COLUMN_MAP
        activity_label: Label of the activity this item belongs to

    Returns:
        tuple: (item_data, compute)
        item_data: Dictionary containing structured data for the item
        compute: Dictionary with compute info if this is a computed field, else None
    """
    # Get type information (column names are mapped to internal names)
    # After NBDC_COLUMN_MAP renaming: 'type_var' -> 'inputType', 'type_data' -> 'dataType'
    type_var = (
        str(row.get("inputType", "")).strip().lower()
        if row.get("inputType") and pd.notna(row.get("inputType"))
        else ""
    )
    type_data = (
        str(row.get("dataType", "")).strip().lower()
        if row.get("dataType") and pd.notna(row.get("dataType"))
        else ""
    )

    # Determine input and value types
    input_type = get_nbdc_input_type(type_var, type_data)
    value_type = get_nbdc_value_type(type_data or type_var)

    # Get item name (mapped from 'name' to 'item_name')
    item_name = row.get("item_name", "")
    if not item_name or (isinstance(item_name, str) and not item_name.strip()):
        raise ValueError("Row missing required 'item_name' column")

    item_name = str(item_name).strip()

    # Check if this is a computed field
    is_computed = is_compute_field(type_var)
    compute = None
    if is_computed:
        compute = {
            "variableName": item_name,
            "isAbout": f"items/{item_name}",
        }

    # Create base item structure
    item_data = {
        "category": "reproschema:Item",
        "id": item_name,
        "prefLabel": {"en": item_name},
    }

    # Add question if available (mapped from 'label' to 'question')
    question = row.get("question")
    if question and pd.notna(question) and str(question).strip():
        item_data["question"] = parse_html(str(question))

    # For compute fields, use description instead of question
    if is_computed:
        if "question" in item_data:
            item_data["description"] = item_data.pop("question")

    # Set UI properties
    item_data["ui"] = {"inputType": input_type}

    # Set readonly for certain field types
    if is_readonly_field(type_var):
        item_data["ui"]["readonlyValue"] = True

    # Set response options
    response_options = {"valueType": [value_type]}
    item_data["responseOptions"] = response_options

    # Add additional notes from NBDC metadata
    # Note: 'instruction' is included in NBDC_ADDITIONAL_NOTES_COLUMNS and will be
    # added to additionalNotesObj rather than as a separate top-level property.
    # This preserves the instruction information while following ReproSchema conventions.
    for key in NBDC_ADDITIONAL_NOTES_COLUMNS:
        if (
            key in row
            and row.get(key)
            and pd.notna(row.get(key))
            and str(row.get(key)).strip()
        ):
            notes_obj = {
                "source": "nbdc",
                "column": key,
                "value": str(row.get(key)).strip(),
            }
            item_data.setdefault("additionalNotesObj", []).append(notes_obj)

    # Add activity info
    notes_obj = {
        "source": "nbdc",
        "column": "activity",
        "value": activity_label,
    }
    item_data.setdefault("additionalNotesObj", []).append(notes_obj)

    return item_data, compute


def process_nbdc_data(df: pd.DataFrame) -> Tuple[Dict[str, Any], list]:
    """
    Process NBDC data dictionary and extract structured data for items and activities.

    Args:
        df: DataFrame containing the NBDC data dictionary

    Returns:
        tuple: (activities, protocol_activities_order)
        activities: Dictionary containing activity data
        protocol_activities_order: List of activity names in order
    """
    # Make a copy to avoid modifying the original
    df = df.copy()

    # Filter out rows with empty names first (before string conversion)
    df = df[df["name"].notna() & (df["name"].astype(str).str.strip() != "")]

    # Check if DataFrame is empty after filtering
    if len(df) == 0:
        raise ValueError(
            "No valid rows found after filtering empty names. "
            "Please check your input data."
        )

    # Validate required columns
    missing_columns = set(NBDC_COLUMN_REQUIRED) - set(df.columns)
    if missing_columns:
        raise ValueError(
            f"Missing required columns: {', '.join(missing_columns)}"
        )

    # Map column names using NBDC_COLUMN_MAP
    df_mapped = df.rename(columns=NBDC_COLUMN_MAP)

    # Group by activity (table_name)
    activities = {}
    protocol_activities_order = []

    for activity_name, group in df_mapped.groupby("activity_name", sort=False):
        # Skip empty activity names
        if pd.isna(activity_name) or not str(activity_name).strip():
            logger.warning("Some rows have no activity name, skipping")
            continue

        items = []
        items_order = []
        act_addProperties = []
        act_compute = []

        for _, row in group.iterrows():
            try:
                item, compute = process_row(row.to_dict(), activity_name)
                items.append(item)

                # Create addProperties for each item
                add_property = {
                    "variableName": item["id"],
                    "isAbout": f"items/{item['id']}",
                    "isVis": True,
                }

                if compute:
                    act_compute.append(compute)
                    add_property["isVis"] = False
                else:
                    items_order.append(f"items/{item['id']}")

                act_addProperties.append(add_property)

            except Exception as e:
                item_name = row.get("item_name", row.get("name", "<unknown>"))
                logger.warning("Failed to process row %s: %s", item_name, e)
                continue

        # Get activity label
        activity_label = group.iloc[0].get("activity_label", activity_name)
        if pd.notna(activity_label) and str(activity_label).strip():
            activity_label = str(activity_label).strip()
        else:
            activity_label = activity_name

        activities[activity_name] = {
            "items": items,
            "order": items_order,
            "compute": act_compute,
            "addProperties": act_addProperties,
            "label": activity_label,
        }
        protocol_activities_order.append(activity_name)

    return activities, protocol_activities_order


def nbdc2reproschema(
    input_file: str,
    yaml_file: str,
    output_path: str = ".",
    input_format: str = None,
    schema_context_url: Optional[str] = None,
):
    """
    Convert NBDC data dictionary to ReproSchema format.

    Args:
        input_file: Path to input file (Parquet, CSV, or RDS)
        yaml_file: Path to YAML configuration file
        output_path: Path to output directory (default: current directory)
        input_format: Input format hint ("parquet", "csv", "rds").
                     If None, format is auto-detected from file extension.
        schema_context_url: URL for schema context (optional)
    """
    # Validate paths
    input_path = Path(input_file)
    yaml_path = Path(yaml_file)
    output_dir = Path(output_path)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    if not yaml_path.exists():
        raise FileNotFoundError(f"YAML file not found: {yaml_file}")

    # Read protocol configuration
    protocol = read_nbdc_config(yaml_path)
    protocol_name = protocol.get("protocol_name", "NBDC").replace(" ", "_")

    # Add source_version for protocol schema (use NBDC data version or default)
    if "source_version" not in protocol:
        protocol["source_version"] = protocol.get("version", "1.0.0")

    # Set up output directory
    abs_folder_path = output_dir / protocol_name
    abs_folder_path.mkdir(parents=True, exist_ok=True)

    # Set schema context URL
    if schema_context_url is None:
        schema_context_url = CONTEXTFILE_URL

    # Detect format if not specified
    if input_format is None:
        input_format = detect_input_format(input_path)

    # Load NBDC data
    logger.info(
        "Loading NBDC data from %s (format: %s)", input_file, input_format
    )
    df = load_nbdc_data(input_path, input_format)
    logger.info("Loaded %d rows", len(df))

    # Process data
    activities, protocol_activities_order = process_nbdc_data(df)
    logger.info("Found %d activities", len(activities))

    # Create activity schemas
    for activity_name, activity_data in activities.items():
        logger.info("Creating activity: %s", activity_name)
        create_activity_schema(
            activity_name,
            activity_data,
            abs_folder_path,
            protocol.get("version", "1.0.0"),
            schema_context_url,
        )

    # Create protocol schema
    logger.info("Creating protocol: %s", protocol_name)
    create_protocol_schema(
        protocol,
        protocol_activities_order,
        abs_folder_path,
        schema_context_url,
    )

    logger.info("OUTPUT DIRECTORY: %s", abs_folder_path)
    return abs_folder_path
