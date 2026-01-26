"""
Convert NBDC data dictionary from R RDS format to ReproSchema format.

This module handles conversion of NBDC (Neurodata Without Borders/Data Coordinating Center)
study data from R RDS files exported from NBDCtoolsData to ReproSchema JSON-LD.
"""

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from .nbdc_mappings import (
    NBDC_ADDITIONAL_NOTES_COLUMNS,
    NBDC_COLUMN_MAP,
    NBDC_COLUMN_MAP_REVERSE,
    NBDC_COLUMN_REQUIRED,
    NBDC_COMPUTE_TYPES,
    NBDC_INPUT_TYPE_MAP,
    NBDC_READONLY_TYPES,
    get_nbdc_input_type,
    get_nbdc_value_type,
    is_compute_field,
    is_readonly_field,
)
from .context_url import CONTEXTFILE_URL
from .convertutils import (
    create_activity_schema,
    create_protocol_schema,
    parse_html,
    read_check_yaml_config,
)


def export_rda_to_rds(rda_path: Path, study: str, release: str, output_dir: Path) -> Path:
    """
    Export NBDC data from RDA to RDS format using R.

    Args:
        rda_path: Path to lst_dds.rda file
        study: Study name (e.g., "abcd", "hbcd")
        release: Release version (e.g., "6.0")
        output_dir: Directory to save the RDS file

    Returns:
        Path to the exported RDS file
    """
    output_rds = output_dir / f"{study}_{release.replace('.', '_')}.rds"

    # R script to export the data
    r_script = f"""
    library(tidyverse)
    load('{rda_path}')
    df <- lst_dds${study}$'{release}'
    saveRDS(df, '{output_rds}')
    """

    # Run R script
    result = subprocess.run(
        ["R", "--slave", "-e", r_script],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Failed to export RDA to RDS: {result.stderr}")

    return output_rds


def load_nbdc_data(rds_path: Path) -> pd.DataFrame:
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
        raise ValueError(f"Expected single object in RDS file, got {len(result)}")

    df = result[list(result.keys())[0]]
    return df


def process_row(
    row: Dict[str, Any], activity_label: str
) -> Dict[str, Any]:
    """
    Process a single row of NBDC data and return structured data for an item.

    Args:
        row: Dictionary containing all fields from the NBDC data row
        activity_label: Label of the activity this item belongs to

    Returns:
        Dictionary containing structured data for the item
    """
    # Get type information
    type_var = str(row.get("type_var", "")).strip().lower() if row.get("type_var") else ""
    type_data = str(row.get("type_data", "")).strip().lower() if row.get("type_data") else ""

    # Determine input and value types
    input_type = get_nbdc_input_type(type_var, type_data)
    value_type = get_nbdc_value_type(type_data or type_var)

    # Get item name
    item_name = row.get("name", "")
    if not item_name:
        raise ValueError("Row missing required 'name' column")

    # Create base item structure
    item_data = {
        "category": "reproschema:Item",
        "id": item_name,
        "prefLabel": {"en": item_name},
    }

    # Add question if available
    question = row.get("label")
    if question and str(question).strip():
        item_data["question"] = parse_html(str(question))

    # Add instruction if available
    instruction = row.get("instruction")
    if instruction and str(instruction).strip():
        item_data["question"] = item_data.get("question", {})
        if isinstance(item_data["question"], dict):
            item_data["question"]["en"] = str(instruction).strip()
        else:
            item_data["instruction"] = {"en": str(instruction).strip()}

    # For compute fields, use description instead of question
    if is_compute_field(type_var):
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

    # Add unit if available
    unit = row.get("unit")
    if unit and str(unit).strip():
        item_data["unit"] = {"en": str(unit).strip()}

    # Add additional notes from NBDC metadata
    for key in NBDC_ADDITIONAL_NOTES_COLUMNS:
        if key in row and row.get(key) and str(row.get(key)).strip():
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

    return item_data


def process_nbdc_data(df: pd.DataFrame) -> (Dict[str, Any], list):
    """
    Process NBDC data dictionary and extract structured data for items and activities.

    Args:
        df: DataFrame containing the NBDC data dictionary

    Returns:
        tuple: (activities, protocol_activities_order)
        activities: Dictionary containing activity data
        protocol_activities_order: List of activity names in order
    """
    # Replace NaN with empty string
    df = df.astype(str).replace("nan", "")
    df = df.fillna("")

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
        if not activity_name or activity_name == "" or activity_name == "nan":
            print("WARNING: Some rows have no activity name, skipping")
            continue

        items = []
        items_order = []

        for _, row in group.iterrows():
            try:
                item = process_row(row, activity_name)
                items.append(item)
                items_order.append(f"items/{item['id']}")
            except Exception as e:
                print(f"Warning: Failed to process row {row.get('name', '<unknown>')}: {e}")
                continue

        # Get activity label
        activity_label = group.iloc[0].get("activity_label", activity_name)
        if activity_label and str(activity_label).strip() and str(activity_label) != "nan":
            activity_label = str(activity_label).strip()
        else:
            activity_label = activity_name

        activities[activity_name] = {
            "items": items,
            "order": items_order,
            "label": activity_label,
        }
        protocol_activities_order.append(activity_name)

    return activities, protocol_activities_order


def nbdc2reproschema(
    rda_file: str,
    yaml_file: str,
    release: str,
    output_path: str = ".",
    study: str = "abcd",
    schema_context_url: Optional[str] = None,
    use_rds: Optional[str] = None,
):
    """
    Convert NBDC data dictionary to ReproSchema format.

    Args:
        rda_file: Path to lst_dds.rda file
        yaml_file: Path to YAML configuration file
        release: NBDC release version (e.g., "6.0", "6.1")
        output_path: Path to output directory (default: current directory)
        study: Study name (default: "abcd")
        schema_context_url: URL for schema context (optional)
        use_rds: Path to pre-exported RDS file (optional, skips RDA export)
    """
    # Validate paths
    rda_path = Path(rda_file)
    yaml_path = Path(yaml_file)
    output_dir = Path(output_path)

    if not rda_path.exists():
        raise FileNotFoundError(f"RDA file not found: {rda_file}")
    if not yaml_path.exists():
        raise FileNotFoundError(f"YAML file not found: {yaml_file}")

    # Read protocol configuration
    protocol = read_check_yaml_config(yaml_path)
    protocol_name = protocol.get("protocol_name", "NBDC").replace(" ", "_")

    # Set up output directory
    abs_folder_path = output_dir / protocol_name
    abs_folder_path.mkdir(parents=True, exist_ok=True)

    # Set schema context URL
    if schema_context_url is None:
        schema_context_url = CONTEXTFILE_URL

    # Load NBDC data
    if use_rds:
        # Use pre-exported RDS file
        rds_path = Path(use_rds)
        print(f"Using pre-exported RDS file: {rds_path}")
    else:
        # Export RDA to RDS first
        print(f"Exporting RDA to RDS format...")
        rds_path = export_rda_to_rds(rda_path, study, release, output_dir)
        print(f"Exported to: {rds_path}")

    # Load data from RDS
    print(f"Loading NBDC data for {study} release {release}...")
    df = load_nbdc_data(rds_path)
    print(f"Loaded {len(df)} rows")

    # Process data
    activities, protocol_activities_order = process_nbdc_data(df)
    print(f"Found {len(activities)} activities")

    # Create activity schemas
    for activity_name, activity_data in activities.items():
        print(f"Creating activity: {activity_name}")
        create_activity_schema(
            activity_name,
            activity_data,
            abs_folder_path,
            f"{study.upper()} {release}",
            schema_context_url,
        )

    # Create protocol schema
    print(f"Creating protocol: {protocol_name}")
    create_protocol_schema(
        protocol, protocol_activities_order, abs_folder_path, schema_context_url
    )

    print(f"OUTPUT DIRECTORY: {abs_folder_path}")
    return abs_folder_path
