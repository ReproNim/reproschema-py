#!/usr/bin/env python
"""
LORIS to ReproSchema Converter

This script converts LORIS CSV data to the ReproSchema format.
It supports the three-layer structure of ReproSchema:
- Protocol level: Study protocol (e.g., HBCD)
- Activity level: Domains or categories from the CSV (grouped assessments)
- Item level: Individual questions/fields from the CSV

Usage:
    python loris2reproschema.py --csv_file CSVFILE --config_file CONFIGFILE --output_path OUTPUTPATH

Example config.yaml:
    protocol_name: "HBCD"
    protocol_display_name: "HEALthy Brain and Child Development Study"
    protocol_description: "Protocol for the HBCD study"
    loris_version: "1.0.0"
    # The column to use for grouping items into activities
    domain_column: "full_instrument_name"  # Change this to match your CSV
"""

import ast
import json
import os
import re
import shutil
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import yaml
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning

# Suppress common BeautifulSoup warning
warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)

# Context URL for ReproSchema
CONTEXTFILE_URL = "https://raw.githubusercontent.com/ReproNim/reproschema/main/releases/1.0.0/reproschema"

# Default mappings from LORIS CSV columns to ReproSchema properties
DEFAULT_LORIS_TO_REPROSCHEMA_MAP = {
    "activity_name": "full_instrument_name",  # Domain/category for grouping
    "item_name": "name",  # Item identifier
    "question": "question",  # The question text
    "field_type": "field_type",  # Input type (text, select, etc.)
    "response_option_labels": "option_labels",  # Response option labels
    "response_option_values": "option_values",  # Response option values
    "description": "description",  # Item description
    "validation": "data_type",  # Data validation type
    "required": "loris_required",  # If field is required
    "min_value": "redcap_text_validation_min",  # Minimum value for validation
    "max_value": "redcap_text_validation_max",  # Maximum value for validation
    "visibility": "redcap_branching_logic",  # Conditional display logic
    "annotation": "redcap_field_annotation",  # Additional notes
    "matrix_group": "redcap_matrix_group_name",  # Matrix group name
}

# Required columns from LORIS CSV
LORIS_REQUIRED_COLUMNS = ["name", "description"]

# Input type mapping from LORIS to ReproSchema
INPUT_TYPE_MAP = {
    "text": "text",
    "textarea": "textArea",
    "select": "select",
    "dropdown": "select",
    "radio": "radio",
    "checkbox": "checkbox",
    "calc": "number",
    "integer": "number",
    "float": "number",
    "number": "number",
    "date": "date",
    "time": "time",
    "datetime": "dateTime",
    "file": "file",
    "slider": "slider",
    "multi-select": "selectMultiple",
    "multiselect": "selectMultiple",
    "": "text",  # Default
}

# Value type mapping from LORIS to ReproSchema
VALUE_TYPE_MAP = {
    "integer": "xsd:integer",
    "float": "xsd:float",
    "number": "xsd:float",
    "date": "xsd:date",
    "datetime": "xsd:dateTime",
    "time": "xsd:time",
    "text": "xsd:string",
    "string": "xsd:string",
    "boolean": "xsd:boolean",
    "": "xsd:string",  # Default
}

# Compute fields (readonly calculated fields)
COMPUTE_LIST = ["calc", "calculated"]

# Fields for validation min/max
RESPONSE_COND = ["minValue", "maxValue"]

# Additional notes fields to include in the schema
ADDITIONAL_NOTES_LIST = [
    "source_field",
    "source_from",
    "source_respondent",
    "study",
    "data_scope",
    "field_category",
    "field_class",
    "coding_format",
    "collection_platform",
    "collection_required",
    "description_status",
]


def get_context_version(context_url: str) -> str:
    """
    Extracts the version from the context URL.

    Args:
        context_url (str): The URL to the context file.

    Returns:
        str: The version string extracted from the URL, or "1.0.0" if not found.
    """
    match = re.search(r"(\d+\.\d+\.\d+(?:-[a-zA-Z0-9]+)?)", context_url)
    return match.group(1) if match else "1.0.0"


def load_config(config_file: str) -> Dict[str, Any]:
    """
    Load configuration from a YAML file.

    Args:
        config_file (str): Path to the YAML configuration file.

    Returns:
        Dict[str, Any]: The configuration as a dictionary.

    Raises:
        FileNotFoundError: If the config file cannot be found.
        yaml.YAMLError: If the config file has invalid YAML syntax.
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


def normalize_condition(condition_str: str) -> str:
    """
    Normalize a condition string from LORIS by replacing variable references.

    Args:
        condition_str (str): The condition string to normalize.

    Returns:
        str: The normalized condition string.
    """
    if not condition_str or pd.isna(condition_str):
        return ""

    # Handle REDCap-style conditions with [variable] references
    pattern = r"\[(.*?)\]"

    def replace_with_var(match):
        return match.group(1)

    condition = re.sub(pattern, replace_with_var, condition_str)

    # Replace common operators
    condition = condition.replace("=", "==")

    # Remove any trailing/leading whitespace
    return condition.strip()


def parse_html(html_str: str) -> Dict[str, str]:
    """
    Parse HTML content and return a dictionary with the text content.

    Args:
        html_str (str): HTML string to parse.

    Returns:
        Dict[str, str]: Dictionary with 'en' key and text content.
    """
    if not html_str or pd.isna(html_str):
        return {"en": ""}

    try:
        # Use BeautifulSoup to extract text
        if "<" in html_str and ">" in html_str:
            soup = BeautifulSoup(html_str, "html.parser")
            text = soup.get_text(separator=" ").strip()
        else:
            text = html_str.strip()

        # Fix known typos from LORIS data and track them
        original_text = text
        text = text.replace("vaginalintercourse", "vaginal intercourse")
        if "vaginalintercourse" in original_text:
            # Note: We'll track this in the converter method that calls this function
            pass
        text = text.replace("less then usual", "less than usual")
        if "less then usual" in original_text:
            # Note: We'll track this in the converter method that calls this function
            pass

        return {"en": text}
    except Exception as e:
        print(f"Error parsing HTML: {e}")
        return {"en": str(html_str).strip()}


def get_value_type(validation_type: str) -> str:
    """
    Get the XSD value type based on the validation type.

    Args:
        validation_type (str): The validation type from LORIS.

    Returns:
        str: The XSD value type.
    """
    validation_type = validation_type.lower().strip()

    # Direct mapping
    if validation_type in VALUE_TYPE_MAP:
        return VALUE_TYPE_MAP[validation_type]

    # Handle special cases
    if "integer" in validation_type:
        return "xsd:integer"
    elif (
        "float" in validation_type
        or "number" in validation_type
        or "decimal" in validation_type
    ):
        return "xsd:float"
    elif "date" in validation_type:
        return "xsd:date"
    elif "time" in validation_type:
        return "xsd:time"
    elif "email" in validation_type:
        return "xsd:string"  # Special handling for email
    elif "boolean" in validation_type:
        return "xsd:boolean"

    # Default to string
    return "xsd:string"


class ReproSchemaConverter:
    """
    Converts LORIS CSV data to ReproSchema format.

    This class provides methods to transform a LORIS CSV file into a ReproSchema
    compliant directory structure with JSON-LD files for protocols, activities, and items.

    Naming Convention:
    - All names (protocol, activity, item) are sanitized for filesystem safety
    - Special characters are replaced with underscores
    - Multiple consecutive underscores are collapsed to single underscore
    - Leading and trailing underscores are removed
    - Example: "BFY - Benefits/Services, Economic Stress" becomes "BFY_Benefits_Services_Economic_Stress"
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the converter with configuration.

        Args:
            config (Dict[str, Any]): Configuration dictionary from the YAML file.
        """
        self.config = config

        # Get column mappings from config or use defaults
        self.column_mappings = config.get(
            "column_mappings", DEFAULT_LORIS_TO_REPROSCHEMA_MAP
        )

        # Additional notes fields to include (can be customized in config)
        self.additional_notes_list = config.get(
            "additional_notes_fields", ADDITIONAL_NOTES_LIST
        )

        # Field type overrides
        self.field_type_overrides = config.get("field_type_overrides", {})

        # Set up logging
        self.verbose = config.get("verbose", True)

        # Schema context URL
        self.schema_context_url = config.get(
            "schema_context_url", CONTEXTFILE_URL
        )

        # Initialize quality report
        self.quality_report = {
            "timestamp": datetime.now().isoformat(),
            "source_file": None,
            "statistics": {},
            "issues": {
                "typos": [],
                "truncated_names": [],
                "missing_choices": [],
                "redundant_prefixes": [],
                "naming_conventions": [],
                "validation_errors": [],
                "field_type_mismatches": [],
            },
            "fixes_applied": [],
            "warnings": [],
        }

    def log(self, message: str, level: str = "INFO") -> None:
        """Simple logging function"""
        if self.verbose or level != "INFO":
            print(f"[{level}] {message}")

    def analyze_csv_headers(self, df: pd.DataFrame) -> Dict[str, List[str]]:
        """
        Analyze CSV headers and suggest possible mappings.

        Args:
            df (pd.DataFrame): The DataFrame to analyze.

        Returns:
            Dict[str, List[str]]: Suggested column mappings.
        """
        columns = list(df.columns)
        self.log(f"Found CSV columns: {', '.join(columns)}")

        # Look for key columns
        suggestions = {}

        # Look for activity/instrument/domain column
        domain_cols = [
            col
            for col in columns
            if col.lower()
            in [
                "domain",
                "instrument",
                "form",
                "full_instrument_name",
                "category",
                "assessment",
            ]
        ]
        if domain_cols:
            suggestions["domain_column"] = domain_cols[0]
            self.log(f"Suggested domain column: {domain_cols[0]}")

        # Look for item name column
        name_cols = [
            col
            for col in columns
            if col.lower()
            in ["name", "item", "variable", "field", "fieldname"]
        ]
        if name_cols:
            suggestions["item_name"] = name_cols[0]
            self.log(f"Suggested item name column: {name_cols[0]}")

        # Look for question text column
        question_cols = [
            col
            for col in columns
            if col.lower() in ["question", "description", "label", "text"]
        ]
        if question_cols:
            suggestions["question"] = question_cols[0]
            self.log(f"Suggested question column: {question_cols[0]}")

        return suggestions

    def load_csv(
        self, csv_file: str, encoding: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Load and preprocess a CSV file.

        Args:
            csv_file (str): Path to the CSV file.
            encoding (str, optional): Encoding to use for reading the CSV file.

        Returns:
            pd.DataFrame: The loaded and preprocessed DataFrame.

        Raises:
            FileNotFoundError: If the CSV file cannot be found.
            pd.errors.ParserError: If the CSV file cannot be parsed.
        """
        try:
            self.log(f"Loading CSV file: {csv_file}")

            # Check file size limit (100MB = 104,857,600 bytes)
            file_size = os.path.getsize(csv_file)
            max_size = 100 * 1024 * 1024  # 100MB in bytes
            if file_size > max_size:
                raise ValueError(
                    f"CSV file size ({file_size / (1024 * 1024):.1f} MB) exceeds the "
                    f"maximum allowed size of {max_size / (1024 * 1024)} MB. "
                    f"Please use a smaller file or increase the size limit."
                )
            self.log(
                f"File size check passed: {file_size / (1024 * 1024):.1f} MB"
            )

            # Try multiple encodings if none specified
            if encoding:
                df = pd.read_csv(csv_file, encoding=encoding, low_memory=False)
                self.log(f"Using specified encoding: {encoding}")
            else:
                # Try multiple encodings in order
                encodings = [
                    "utf-8",
                    "utf-8-sig",
                    "latin-1",
                    "windows-1252",
                    "cp1252",
                ]
                df = None

                for enc in encodings:
                    try:
                        df = pd.read_csv(
                            csv_file, encoding=enc, low_memory=False
                        )
                        self.log(f"Successfully read CSV with {enc} encoding")
                        break
                    except UnicodeDecodeError:
                        self.log(
                            f"Failed to decode with {enc}, trying next encoding...",
                            "DEBUG",
                        )

                if df is None:
                    raise ValueError(
                        "Failed to read CSV file with any of the attempted encodings. "
                        "Please check the file encoding or specify it with --encoding."
                    )

            # Clean up column names
            df.columns = df.columns.str.strip().str.replace('"', "")

            # Analyze CSV and suggest mappings
            suggestions = self.analyze_csv_headers(df)

            # Update domain column from config or suggestions
            domain_col = self.config.get("domain_column")
            if not domain_col and "domain_column" in suggestions:
                domain_col = suggestions["domain_column"]
                self.log(f"Using suggested domain column: {domain_col}")

            # If we found a domain column, update the mapping
            if domain_col:
                self.column_mappings["activity_name"] = domain_col
                self.log(f"Using '{domain_col}' as the domain/activity column")

            # Validate required columns are present
            required_cols = [
                self.column_mappings[col] for col in ["item_name"]
            ]
            missing_cols = [
                col for col in required_cols if col not in df.columns
            ]
            if missing_cols:
                self.log(
                    f"Warning: Required columns missing: {', '.join(missing_cols)}",
                    "WARNING",
                )

            return self.preprocess_fields(df)
        except FileNotFoundError:
            raise FileNotFoundError(f"CSV file not found: {csv_file}")
        except pd.errors.ParserError:
            raise pd.errors.ParserError(f"Error parsing CSV file: {csv_file}")
        except Exception as e:
            raise Exception(f"Error loading CSV: {str(e)}")

    def preprocess_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Preprocess fields in the DataFrame, cleaning up special fields.

        Args:
            df (pd.DataFrame): The DataFrame to preprocess.

        Returns:
            pd.DataFrame: The preprocessed DataFrame.
        """
        self.log(f"Preprocessing {len(df)} rows")

        # Replace NaN values with empty strings
        df = df.fillna("")

        # Clean up HTML, escape characters, etc. in all string columns
        for col in df.columns:
            if df[col].dtype == "object":  # Only process string columns
                df[col] = df[col].apply(
                    lambda x: (
                        str(x)
                        .replace("&gt;", ">")
                        .replace("&lt;", "<")
                        .replace("\n", " ")
                        .replace("\r", " ")
                        if isinstance(x, str)
                        else x
                    )
                )

        # If there's no domain column, create one with a default value
        domain_col = self.column_mappings["activity_name"]
        if domain_col not in df.columns:
            default_domain = self.config.get("default_domain", "Unknown")
            self.log(
                f"Warning: Domain column '{domain_col}' not found. Creating it with value '{default_domain}'",
                "WARNING",
            )
            df[domain_col] = default_domain

        return df

    def process_input_value_types(
        self, field_type: str, data_type: str
    ) -> Tuple[str, str, Optional[Dict]]:
        """
        Process input type and value type to determine the final input type and value type.

        Args:
            field_type (str): Input type from LORIS
            data_type (str): Data type from LORIS

        Returns:
            tuple: (input_type, value_type, additional_notes)
            input_type (str): Final input type for ReproSchema
            value_type (str): Final value type for ReproSchema
            additional_notes (dict): Additional notes about custom types, or None
        """
        additional_notes = None

        # Check field type overrides first
        if field_type in self.field_type_overrides:
            field_type = self.field_type_overrides[field_type]

        # Convert to lowercase for consistency
        field_type = field_type.lower().strip() if field_type else ""
        data_type = data_type.lower().strip() if data_type else ""

        # Determine input type
        if field_type in INPUT_TYPE_MAP:
            input_type = INPUT_TYPE_MAP[field_type]
        else:
            # Try to find the closest match
            for key, value in INPUT_TYPE_MAP.items():
                if key and key in field_type:
                    input_type = value
                    break
            else:
                input_type = "text"  # Default fallback
                additional_notes = {
                    "source": "loris",
                    "column": "field_type",
                    "value": field_type,
                }

        # Determine value type
        try:
            # Get standard value type
            value_type = get_value_type(data_type)
        except ValueError:
            # If not recognized, default to string
            value_type = "xsd:string"
            if data_type:  # Only add note if data_type was non-empty
                additional_notes = {
                    "source": "loris",
                    "column": "data_type",
                    "value": data_type,
                }

        # Adjust input type based on value type for consistency
        if value_type == "xsd:date" and field_type == "text":
            input_type = "date"
        elif data_type == "integer" and field_type == "text":
            input_type = "number"
        elif data_type in ["float", "number"] and field_type == "text":
            input_type = "number"

        return input_type, value_type, additional_notes

    def process_response_options(
        self, row: Dict[str, Any], item_name: str
    ) -> Tuple[Dict[str, Any], Optional[Dict]]:
        """
        Process response options from LORIS format to ReproSchema format.

        Args:
            row (Dict[str, Any]): The row data.
            item_name (str): The name of the item being processed.

        Returns:
            tuple: (response_options, additional_notes)
            response_options (Dict): The processed response options
            additional_notes (Dict): Additional notes if any
        """
        # Get field type and determine if it's multiple choice
        field_type_col = self.column_mappings["field_type"]
        field_type = str(row.get(field_type_col, "")).lower().strip()

        # Check field type overrides
        if field_type in self.field_type_overrides:
            field_type = self.field_type_overrides[field_type]

        # Get data type for value type
        data_type_col = self.column_mappings["validation"]
        data_type = str(row.get(data_type_col, "")).lower().strip()

        # Process input and value types
        input_type, value_type, type_notes = self.process_input_value_types(
            field_type, data_type
        )

        # Default response options
        response_options = {"valueType": [value_type]}
        additional_notes = type_notes

        # Check if this is multiple choice
        is_multiple_choice = (
            "multi" in field_type.lower() or "checkbox" in field_type.lower()
        )
        if is_multiple_choice:
            response_options["multipleChoice"] = True

        # Process choices if available
        labels_col = self.column_mappings["response_option_labels"]
        values_col = self.column_mappings["response_option_values"]

        if (
            labels_col in row
            and values_col in row
            and row.get(labels_col)
            and row.get(values_col)
        ):

            choices, value_types = self.process_choices(
                row.get(labels_col), row.get(values_col), item_name
            )

            if choices:
                response_options["choices"] = choices
                response_options["valueType"] = value_types

        # Add validation constraints if available
        min_val_col = self.column_mappings["min_value"]
        max_val_col = self.column_mappings["max_value"]

        if min_val_col in row and row.get(min_val_col):
            try:
                min_val = row.get(min_val_col)
                response_options["minValue"] = (
                    float(min_val) if "." in str(min_val) else int(min_val)
                )
            except (ValueError, TypeError):
                self.log(
                    f"Warning: Invalid min value for {item_name}: {row.get(min_val_col)}",
                    "WARNING",
                )

        if max_val_col in row and row.get(max_val_col):
            try:
                max_val = row.get(max_val_col)
                response_options["maxValue"] = (
                    float(max_val) if "." in str(max_val) else int(max_val)
                )
            except (ValueError, TypeError):
                self.log(
                    f"Warning: Invalid max value for {item_name}: {row.get(max_val_col)}",
                    "WARNING",
                )

        return response_options, additional_notes

    def process_choices(
        self, labels_str: str, values_str: str, item_name: str
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Process choices from labels and values strings.

        Args:
            labels_str (str): The response option labels string.
            values_str (str): The response option values string.
            item_name (str): The name of the item being processed.

        Returns:
            tuple: (choices, value_types)
            choices (List[Dict]): List of dictionaries with 'name' and 'value' keys
            value_types (List[str]): List of XSD types for the values
        """
        if (
            pd.isna(labels_str)
            or pd.isna(values_str)
            or not labels_str
            or not values_str
        ):
            return [], ["xsd:string"]

        choices = []
        value_types = set(["xsd:string"])  # Default to string

        try:
            # Check if potentially JSON format (starts with [ and ends with ])
            if (
                str(labels_str).startswith("[")
                and str(labels_str).endswith("]")
            ) or (
                str(values_str).startswith("[")
                and str(values_str).endswith("]")
            ):
                try:
                    # Try to parse with ast.literal_eval first (safer for Python-like list strings)
                    labels = ast.literal_eval(str(labels_str))
                    values = ast.literal_eval(str(values_str))
                    if not isinstance(labels, list) or not isinstance(
                        values, list
                    ):
                        raise ValueError(
                            "Parsed labels or values are not lists"
                        )
                    if len(labels) != len(values):
                        self.log(
                            f"Warning: Mismatch in number of labels and values for {item_name} after ast.literal_eval. Labels: {labels_str}, Values: {values_str}",
                            "WARNING",
                        )
                        return [], ["xsd:string"]

                except (ValueError, SyntaxError):
                    # ast.literal_eval failed - fall back to string splitting
                    # Using simple split instead of json.loads to avoid issues
                    # with apostrophes in labels (e.g., "don't know")
                    self.log(
                        f"ast.literal_eval failed for {item_name}, falling back to split",
                        "DEBUG",
                    )
                    # Remove brackets and split by commas
                    labels = [
                        label_str.strip()
                        for label_str in str(labels_str).strip("[]").split(",")
                    ]
                    values = [
                        v.strip()
                        for v in str(values_str).strip("[]").split(",")
                    ]
                    if len(labels) != len(values):
                        self.log(
                            f"Warning: Mismatch in number of labels and values for {item_name} after string split. Labels: {labels_str}, Values: {values_str}",
                            "WARNING",
                        )
                        return [], ["xsd:string"]
            elif "|" in str(labels_str):
                # Split by pipe character
                labels = [
                    label_str.strip()
                    for label_str in str(labels_str).split("|")
                ]
                values = [v.strip() for v in str(values_str).split("|")]
            elif "," in str(labels_str):
                # Split by comma
                labels = [
                    label_str.strip()
                    for label_str in str(labels_str).split(",")
                ]
                values = [v.strip() for v in str(values_str).split(",")]
            else:
                # Try to handle as a single value
                labels = [str(labels_str).strip()]
                values = [str(values_str).strip()]

            # Create choices from labels and values
            for label, value in zip(labels, values):
                # Clean up quotes if they exist
                label = str(label).strip().strip("\"'")
                value = str(value).strip().strip("\"'")

                # Skip 'NULL' labels which are typically empty options
                if label.upper() == "NULL" or label == "":
                    continue

                # Determine value type and convert value
                if value == "0":
                    value_num = 0
                    value_types.add("xsd:integer")
                    choices.append({"name": {"en": label}, "value": value_num})
                elif value.isdigit():
                    # Check if starts with 0 but isn't just 0 (e.g., "01", "02")
                    if value[0] == "0" and len(value) > 1:
                        # Treat as string to preserve leading zeros
                        choices.append({"name": {"en": label}, "value": value})
                    else:
                        value_num = int(value)
                        value_types.add("xsd:integer")
                        choices.append(
                            {"name": {"en": label}, "value": value_num}
                        )
                elif re.match(r"^-?\d+(\.\d+)?$", value):
                    value_num = float(value)
                    value_types.add("xsd:float")
                    choices.append({"name": {"en": label}, "value": value_num})
                else:
                    # Keep as string
                    choices.append({"name": {"en": label}, "value": value})

        except Exception as e:
            self.log(
                f"Warning: Error processing response options for {item_name}: {str(e)}",
                "WARNING",
            )

        # Check if we have at least one valid choice
        if not choices:
            self.log(f"No valid choices found for {item_name}", "DEBUG")
            return [], ["xsd:string"]

        return choices, list(value_types)

    def process_preamble(
        self, row: Dict[str, Any], prior_preamble_info: Optional[Dict] = None
    ) -> Tuple[Dict[str, str], Optional[Dict]]:
        """
        Process preamble information from the row.

        Args:
            row (Dict[str, Any]): Row data from CSV
            prior_preamble_info (Dict[str, Any], optional): Preamble information from previous row

        Returns:
            tuple: (preamble, preamble_info_propagate)
            preamble (Dict[str, str]): Preamble text for the current item
            preamble_info_propagate (Dict): Preamble information to propagate to next row
        """
        preamble_text = None

        # Check if there's conditional logic that should be converted to preamble
        visibility_col = self.column_mappings.get("visibility")
        if visibility_col and visibility_col in row and row[visibility_col]:
            condition = normalize_condition(row[visibility_col])
            if condition:
                preamble_text = {"en": f"Conditional display: {condition}"}
                return (
                    preamble_text,
                    None,
                )  # Don't propagate this type of preamble

        # If no preamble found, return None
        return None, None

    def process_item(
        self, row: Dict[str, Any], prior_preamble_info: Optional[Dict] = None
    ) -> Tuple[Dict[str, Any], Optional[Dict], Optional[Dict], Dict[str, Any]]:
        """
        Process a single row from the CSV into a ReproSchema item.

        Args:
            row (Dict[str, Any]): A dictionary representing a row from the CSV.
            prior_preamble_info (Dict, optional): Preamble info from previous row.

        Returns:
            tuple: (item_data, preamble_info_propagate, compute, addProperties)
            item_data (Dict): Dictionary representing a ReproSchema item
            preamble_info_propagate (Dict): Preamble info to propagate to next row
            compute (Dict): Compute expression if this is a computed field
            addProperties (Dict): Properties for the activity schema
        """
        # Get item name or use a fallback if not available
        item_name_col = self.column_mappings["item_name"]
        item_name = row.get(item_name_col, "")
        if not item_name or pd.isna(item_name):
            # Try source_field as fallback
            if (
                "source_field" in row
                and row["source_field"]
                and not pd.isna(row["source_field"])
            ):
                item_name = row["source_field"]
            else:
                # Generate a unique name as last resort
                import hashlib

                item_hash = hashlib.md5(str(row).encode()).hexdigest()[:8]
                item_name = f"item_{item_hash}"
                self.log(
                    f"Warning: Empty item name, using generated name: {item_name}",
                    "WARNING",
                )

        # Fix redundant prefix in item names (e.g., sed_cg_foodins_sed_cg_foodins_category -> sed_cg_foodins_category)
        # This pattern occurs when the instrument prefix is duplicated in the variable name
        if item_name and "_" in item_name:
            parts = item_name.split("_")
            # Check if we have a pattern like prefix_prefix_suffix
            if len(parts) >= 3:
                # Find potential duplicated prefix
                for i in range(1, len(parts)):
                    potential_prefix = "_".join(parts[:i])
                    remaining = "_".join(parts[i:])
                    if remaining.startswith(potential_prefix + "_"):
                        # Found a redundant prefix
                        item_name = remaining
                        self.log(
                            f"Fixed redundant prefix in item name: {item_name}",
                            "DEBUG",
                        )
                        break

        # Clean up item name for use as an ID
        # Step 1: Replace all non-alphanumeric characters (except underscore) with underscore
        item_id = re.sub(r"[^a-zA-Z0-9_]", "_", str(item_name))
        # Step 2: Collapse multiple consecutive underscores into a single underscore
        # Step 3: Remove leading and trailing underscores
        # Example: "__item__name___" becomes "item_name"
        item_id = re.sub(r"_+", "_", item_id).strip("_")

        # Get question text - first try question, then fall back to description if needed
        question_col = self.column_mappings["question"]
        question_text = row.get(question_col, "")
        if pd.isna(question_text) or question_text == "":
            # Try description as fallback
            description_col = self.column_mappings["description"]
            question_text = row.get(description_col, item_name)
            if pd.isna(question_text):
                question_text = item_name

        # Parse HTML in question text
        question_text = parse_html(question_text)

        # Get field type
        field_type_col = self.column_mappings["field_type"]
        field_type = str(row.get(field_type_col, "")).lower()

        # Get data type for value type mapping
        data_type_col = self.column_mappings["validation"]
        data_type = str(row.get(data_type_col, ""))

        # Process input and value types
        input_type, value_type, type_notes = self.process_input_value_types(
            field_type, data_type
        )

        # Initialize item data
        item_data = {
            "@context": self.schema_context_url,
            "category": "reproschema:Item",
            "id": item_id,
            "prefLabel": {"en": item_name},
            "question": question_text,
            "ui": {"inputType": input_type},
        }

        # Process response options
        response_options, choices_notes = self.process_response_options(
            row, item_name
        )
        item_data["responseOptions"] = response_options

        # If we have choices but inputType is text, update to select
        if (
            "choices" in response_options
            and response_options["choices"]
            and input_type == "text"
        ):
            input_type = "select"
            item_data["ui"]["inputType"] = input_type

        # If inputType is select but no choices provided, add empty choices array
        # This prevents rendering issues but indicates that choices need to be configured
        if (
            input_type in ["select", "selectMultiple"]
            and "choices" not in response_options
        ):
            response_options["choices"] = []
            # Add a note about missing choices
            if not choices_notes:
                choices_notes = {
                    "note": "Choices need to be configured for this select field"
                }

        # Add description if available and different from question
        description_col = self.column_mappings["description"]
        description = row.get(description_col, "")
        if (
            description
            and not pd.isna(description)
            and parse_html(description) != question_text
        ):
            item_data["description"] = parse_html(description)

        # Process preamble (conditional logic)
        preamble, preamble_info_propagate = self.process_preamble(
            row, prior_preamble_info
        )
        if preamble:
            item_data["preamble"] = preamble

        # Check if this is a compute field
        compute = None
        if field_type.lower() in COMPUTE_LIST:
            # If this is a computed field, create compute expression
            expression = ""
            if "choices" in row and row["choices"]:
                expression = normalize_condition(row["choices"])
            compute = {"variableName": item_id, "jsExpression": expression}
            # For compute items, we use description instead of question
            if "question" in item_data and "description" not in item_data:
                item_data["description"] = item_data.pop("question")
            # Mark as readonly
            item_data["ui"]["readonlyValue"] = True

        # Check annotation for readonly/hidden
        annotation_col = self.column_mappings.get("annotation")
        if annotation_col and annotation_col in row:
            annotation_val = row[annotation_col]
            if pd.notna(annotation_val) and annotation_val:
                annotation = annotation_val.upper()
                if (
                    "@READONLY" in annotation
                    or "@HIDDEN" in annotation
                    or "@CALCTEXT" in annotation
                ):
                    item_data["ui"]["readonlyValue"] = True

        # Add required flag
        required_col = self.column_mappings["required"]
        required = row.get(required_col, "")
        is_required = False
        if required and not pd.isna(required):
            if isinstance(required, bool):
                is_required = required
            elif str(required).lower() in (
                "y",
                "yes",
                "true",
                "1",
                "required",
                "optional",
            ):
                is_required = str(required).lower() in (
                    "y",
                    "yes",
                    "true",
                    "1",
                    "required",
                )

        # Add additional notes from configured columns
        additional_notes = []
        if type_notes:
            additional_notes.append(type_notes)
        if choices_notes:
            additional_notes.append(choices_notes)

        for column in self.additional_notes_list:
            if (
                column in row
                and not pd.isna(row[column])
                and row[column] != ""
            ):
                additional_notes.append(
                    {
                        "source": "loris",
                        "column": column,
                        "value": str(row[column]),
                    }
                )

        if additional_notes:
            item_data["additionalNotesObj"] = additional_notes

        # Set up addProperties for activity schema
        addProperties = {
            "variableName": item_id,
            "isAbout": f"items/{item_id}",
            "valueRequired": is_required,
            "isVis": True,
        }

        # Handle visibility based on annotation
        if annotation_col and annotation_col in row:
            annotation_val = row[annotation_col]
            if pd.notna(annotation_val) and annotation_val:
                annotation = annotation_val.upper()
                if "@HIDDEN" in annotation:
                    addProperties["isVis"] = False

        # Computed fields are typically hidden
        if compute:
            addProperties["isVis"] = False

        # Handle conditional display logic
        visibility_col = self.column_mappings.get("visibility")
        if visibility_col and visibility_col in row and row[visibility_col]:
            condition = normalize_condition(row[visibility_col])
            if condition:
                addProperties["isVis"] = condition

        return item_data, preamble_info_propagate, compute, addProperties

    def process_dataframe(self, df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        """
        Process the entire DataFrame into activities and items.

        Args:
            df (pd.DataFrame): The DataFrame to process.

        Returns:
            Dict[str, Dict[str, Any]]: A dictionary of activities, each containing items.
        """
        activities = {}

        # Get primary domain column and fallbacks
        primary_domain_col = self.column_mappings["activity_name"]
        fallback_domain_col = self.config.get(
            "fallback_domain_column", "domain"
        )
        default_domain = self.config.get("default_domain", "Unknown")

        # Ensure we have some domain column
        if (
            primary_domain_col not in df.columns
            and fallback_domain_col not in df.columns
        ):
            self.log(
                f"Warning: Neither primary domain column '{primary_domain_col}' nor fallback '{fallback_domain_col}' found. Using default '{default_domain}'",
                "WARNING",
            )
            df["temp_domain"] = default_domain
            domain_col = "temp_domain"
        elif primary_domain_col not in df.columns:
            self.log(
                f"Warning: Primary domain column '{primary_domain_col}' not found. Using fallback '{fallback_domain_col}'",
                "WARNING",
            )
            domain_col = fallback_domain_col
        else:
            domain_col = primary_domain_col

        # Create a new column that merges the primary and fallback domains
        df["effective_domain"] = df[domain_col].copy()

        # If fallback exists and primary domain column exists but has empty values, use fallback
        if (
            fallback_domain_col in df.columns
            and primary_domain_col in df.columns
        ):
            mask = df[primary_domain_col].isna() | (
                df[primary_domain_col] == ""
            )
            if (
                fallback_domain_col in df.columns
            ):  # Double-check to avoid KeyError
                df.loc[mask, "effective_domain"] = df.loc[
                    mask, fallback_domain_col
                ]

        # If there are still empty domains, use the default
        mask = df["effective_domain"].isna() | (df["effective_domain"] == "")
        df.loc[mask, "effective_domain"] = default_domain

        # Group rows by effective domain
        domain_groups = df.groupby("effective_domain")
        num_domains = len(domain_groups)
        self.log(
            f"Found {num_domains} unique domains/activities after applying fallbacks"
        )

        total_items = 0
        for domain, group in domain_groups:
            # Skip empty domains (shouldn't happen now with fallbacks)
            if pd.isna(domain) or domain == "":
                continue

            domain_str = str(domain).strip()
            if domain_str == "":
                domain_str = default_domain

            item_count = len(group)
            self.log(
                f"Processing domain: {domain_str} with {item_count} items"
            )
            total_items += item_count

            # Process each row into an item
            items = []
            act_addProperties = []
            act_compute = []
            act_items_order = []
            act_preamble = []
            item_preamble_info = None

            for _, row in group.iterrows():
                try:
                    item, item_preamble_info, compute, addProperty = (
                        self.process_item(
                            row, prior_preamble_info=item_preamble_info
                        )
                    )
                    items.append(item)
                    act_addProperties.append(addProperty)

                    if compute:
                        act_compute.append(compute)
                    else:
                        act_items_order.append(f"items/{item['id']}")
                        if item.get("preamble"):
                            act_preamble.append(item["preamble"]["en"])
                except Exception as e:
                    self.log(
                        f"Error processing item in domain {domain_str}: {str(e)}",
                        "ERROR",
                    )
                    import traceback

                    self.log(traceback.format_exc(), "DEBUG")

            # Create activity data
            activities[domain_str] = {
                "items": items,
                "order": act_items_order,
                "compute": act_compute,
                "addProperties": act_addProperties,
            }

            # Check if all preambles are the same for all questions
            # If so, make it an activity-level preamble
            act_compute_name = [c["variableName"] for c in act_compute]
            if (
                act_preamble
                and len(set(act_preamble)) == 1
                and len(act_preamble) == len(act_items_order)
            ):
                activities[domain_str]["preamble"] = {"en": act_preamble[0]}
                for item in items:
                    # Remove duplicate preambles from items
                    if item["id"] in act_compute_name:
                        if item.get("preamble") == {"en": act_preamble[0]}:
                            del item["preamble"]
                    else:
                        del item["preamble"]

        self.log(
            f"Successfully processed {total_items} items into {len(activities)} activities"
        )
        return activities

    def create_activity_schema(
        self,
        activity_name: str,
        activity_data: Dict[str, Any],
        output_path: Path,
        version: str,
    ) -> None:
        """
        Create a ReproSchema activity schema file.

        Args:
            activity_name (str): The name of the activity.
            activity_data (Dict[str, Any]): The activity data including items.
            output_path (Path): The base output path.
            version (str): The version string to include in the schema.
        """
        # Fix truncated activity names from LORIS data
        if activity_name.endswith(" ("):
            # This appears to be a truncated name
            original_name = activity_name
            activity_name = activity_name[
                :-2
            ].strip()  # Remove the incomplete parenthesis
            self.log(
                f"Warning: Fixed truncated activity name to: {activity_name}",
                "WARNING",
            )
            self.quality_report["issues"]["truncated_names"].append(
                {"original": original_name, "fixed": activity_name}
            )
            self.quality_report["fixes_applied"].append(
                f"Fixed truncated activity name: {original_name}"
            )

        # Handle special characters in activity name
        # Step 1: Replace all non-alphanumeric characters (except underscore) with underscore
        safe_activity_name = re.sub(r"[^a-zA-Z0-9_]", "_", str(activity_name))
        # Step 2: Collapse multiple consecutive underscores into a single underscore
        # Step 3: Remove leading and trailing underscores
        # Example: "BFY - Benefits/Services, Economic Stress" becomes "BFY_Benefits_Services_Economic_Stress"
        safe_activity_name = re.sub(r"_+", "_", safe_activity_name).strip("_")

        # Create activity schema
        activity_schema = {
            "@context": self.schema_context_url,
            "category": "reproschema:Activity",
            "id": f"{safe_activity_name}_schema",
            "prefLabel": {"en": activity_name},
            "description": {"en": f"Questions related to {activity_name}"},
            "schemaVersion": get_context_version(self.schema_context_url),
            "version": version,
            "ui": {
                "order": activity_data["order"],
                "addProperties": activity_data["addProperties"],
                "shuffle": False,
            },
        }

        # Add compute section if there are computed fields
        if activity_data["compute"]:
            activity_schema["compute"] = activity_data["compute"]

        # Add preamble if available
        if "preamble" in activity_data:
            activity_schema["preamble"] = activity_data["preamble"]

        # Ensure output directories exist
        activity_dir = output_path / "activities" / safe_activity_name
        activity_dir.mkdir(parents=True, exist_ok=True)

        items_dir = activity_dir / "items"
        items_dir.mkdir(parents=True, exist_ok=True)

        # Write activity schema
        schema_path = activity_dir / f"{safe_activity_name}_schema"
        with open(schema_path, "w", encoding="utf-8") as f:
            json.dump(activity_schema, f, indent=2)

        # Write each item
        for item in activity_data["items"]:
            item_path = items_dir / f"{item['id']}"
            with open(item_path, "w", encoding="utf-8") as f:
                json.dump(item, f, indent=2)

        self.log(
            f"{activity_name} activity schema created with {len(activity_data['items'])} items"
        )

    def create_protocol_schema(
        self,
        protocol_name: str,
        protocol_data: Dict[str, Any],
        activities: List[str],
        output_path: Path,
    ) -> None:
        """
        Create a ReproSchema protocol schema file.

        Args:
            protocol_name (str): The name of the protocol.
            protocol_data (Dict[str, Any]): The protocol configuration data.
            activities (List[str]): List of activity names to include.
            output_path (Path): The base output path.
        """
        # Handle special characters in protocol name
        # Convert to filesystem-safe name by replacing special characters with underscores
        safe_protocol_name = re.sub(r"[^a-zA-Z0-9_]", "_", protocol_name)
        # Clean up multiple underscores for better readability
        safe_protocol_name = re.sub(r"_+", "_", safe_protocol_name).strip("_")

        # Create safe activity names
        # Apply same sanitization to all activity names for consistency
        safe_activities = []
        for act in activities:
            safe_name = re.sub(r"[^a-zA-Z0-9_]", "_", str(act))
            safe_name = re.sub(r"_+", "_", safe_name).strip("_")
            safe_activities.append(safe_name)

        # Create protocol schema
        protocol_schema = {
            "@context": self.schema_context_url,
            "category": "reproschema:Protocol",
            "id": f"{safe_protocol_name}_schema",
            "prefLabel": {
                "en": protocol_data.get("protocol_display_name", protocol_name)
            },
            "description": {
                "en": protocol_data.get(
                    "protocol_description", f"Protocol for {protocol_name}"
                )
            },
            "schemaVersion": get_context_version(self.schema_context_url),
            "version": protocol_data.get("loris_version", "1.0.0"),
            "ui": {
                "addProperties": [
                    {
                        "isAbout": f"../activities/{safe_act}/{safe_act}_schema",
                        "variableName": f"{safe_act}_schema",
                        "prefLabel": {"en": act.replace("_", " ").title()},
                        "isVis": True,
                    }
                    for act, safe_act in zip(activities, safe_activities)
                ],
                "order": [
                    f"../activities/{safe_act}/{safe_act}_schema"
                    for safe_act in safe_activities
                ],
                "shuffle": False,
            },
        }

        # Add preamble if available
        if protocol_data.get("protocol_preamble"):
            protocol_schema["preamble"] = {
                "en": protocol_data["protocol_preamble"]
            }

        # Ensure protocol directory exists
        protocol_dir = output_path / safe_protocol_name
        protocol_dir.mkdir(parents=True, exist_ok=True)

        # Write protocol schema
        schema_path = protocol_dir / f"{safe_protocol_name}_schema"
        with open(schema_path, "w", encoding="utf-8") as f:
            json.dump(protocol_schema, f, indent=2)

        self.log(f"Protocol schema created at {schema_path}")

    def clean_output_directories(self, output_path: Path) -> None:
        """
        Clean up the output directories, removing existing folders.

        Args:
            output_path (Path): The base output path to clean.
        """
        if output_path.exists():
            for item in output_path.iterdir():
                if item.is_dir():
                    try:
                        shutil.rmtree(item)
                        self.log(f"Removed directory: {item}")
                    except Exception as e:
                        self.log(
                            f"Warning: Could not remove directory {item}: {str(e)}",
                            "WARNING",
                        )
            self.log(f"Cleaned folders in output directory: {output_path}")
        else:
            self.log(
                f"Output directory does not exist, will be created: {output_path}"
            )

    def save_quality_report(self, output_path: Path) -> None:
        """
        Save the quality report to a JSON file.

        Args:
            output_path (Path): The output directory path.
        """
        report_file = (
            output_path.parent
            / f"quality_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(self.quality_report, f, indent=2)
        self.log(f"Quality report saved to: {report_file}")

    def remove_ds_store(self, directory: Path) -> None:
        """
        Remove all .DS_Store files in the given directory and its subdirectories.

        Args:
            directory (Path): The directory to clean.
        """
        for root, _dirs, files in os.walk(directory):
            for file in files:
                if file == ".DS_Store":
                    try:
                        file_path = Path(root) / file
                        file_path.unlink()
                        self.log(f"Removed .DS_Store file: {file_path}")
                    except Exception as e:
                        self.log(
                            f"Warning: Could not remove file {file_path}: {str(e)}",
                            "WARNING",
                        )

    def analyze_csv(
        self, csv_file: str, encoding: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze the CSV file structure and suggest mappings.

        Args:
            csv_file (str): Path to the CSV file to analyze.
            encoding (str, optional): Encoding to use for reading the CSV.

        Returns:
            Dict[str, Any]: Suggested mappings and CSV statistics.
        """
        try:
            # Load the CSV file
            df = self.load_csv(csv_file, encoding)

            # Get column information
            columns = list(df.columns)

            # Check if common column names exist
            domain_suggestions = [
                col
                for col in columns
                if col.lower()
                in [
                    "domain",
                    "instrument",
                    "form",
                    "category",
                    "assessment",
                    "full_instrument_name",
                ]
            ]

            name_suggestions = [
                col
                for col in columns
                if col.lower()
                in ["name", "item", "variable", "field", "fieldname"]
            ]

            question_suggestions = [
                col
                for col in columns
                if col.lower() in ["question", "description", "text", "label"]
            ]

            # Look for response options
            option_label_suggestions = [
                col
                for col in columns
                if "label" in col.lower() or "option" in col.lower()
            ]
            option_value_suggestions = [
                col
                for col in columns
                if "value" in col.lower() or "option" in col.lower()
            ]

            # Look for field type columns
            field_type_suggestions = [
                col
                for col in columns
                if "type" in col.lower() or "field" in col.lower()
            ]

            # Build suggested mappings
            suggested_mappings = {}
            if domain_suggestions:
                suggested_mappings["activity_name"] = domain_suggestions[0]

            if name_suggestions:
                suggested_mappings["item_name"] = name_suggestions[0]

            if question_suggestions:
                suggested_mappings["question"] = question_suggestions[0]

            if field_type_suggestions:
                suggested_mappings["field_type"] = field_type_suggestions[0]

            if option_label_suggestions:
                suggested_mappings["response_option_labels"] = (
                    option_label_suggestions[0]
                )

            if option_value_suggestions:
                suggested_mappings["response_option_values"] = (
                    option_value_suggestions[0]
                )

            # Sample value counts for potential domain columns
            domain_value_counts = {}
            for col in domain_suggestions:
                if col in df.columns:
                    value_counts = df[col].value_counts()
                    domain_value_counts[col] = {
                        "unique_values": len(value_counts),
                        "top_values": value_counts.head(5).to_dict(),
                    }

            # Look for field type distributions
            field_type_distributions = {}
            for col in field_type_suggestions:
                if col in df.columns:
                    type_counts = df[col].value_counts()
                    field_type_distributions[col] = {
                        "unique_types": len(type_counts),
                        "top_types": type_counts.head(10).to_dict(),
                    }

            return {
                "columns": columns,
                "sample_rows": len(df),
                "suggested_mappings": suggested_mappings,
                "domain_analysis": domain_value_counts,
                "field_type_analysis": field_type_distributions,
            }

        except Exception as e:
            self.log(f"Error analyzing CSV: {str(e)}", "ERROR")
            return {"error": str(e)}

    def convert(
        self, csv_file: str, output_path: str, encoding: Optional[str] = None
    ) -> None:
        """
        Convert a CSV file to ReproSchema format.

        Args:
            csv_file (str): Path to the input CSV file.
            output_path (str): Path to the output directory.
            encoding (str, optional): Encoding to use for reading the CSV.

        Raises:
            Various exceptions with descriptive error messages.
        """
        try:
            # Validate output path to prevent directory traversal
            if ".." in output_path:
                raise ValueError(
                    f"Output path '{output_path}' contains directory traversal patterns"
                )

            # Get protocol name from config or use a default
            protocol_name = self.config.get("protocol_name", "LORIS_Protocol")
            # Sanitize protocol name for filesystem safety
            safe_protocol_name = re.sub(r"[^a-zA-Z0-9_]", "_", protocol_name)
            # Clean up multiple underscores for better readability
            safe_protocol_name = re.sub(r"_+", "_", safe_protocol_name).strip(
                "_"
            )

            # Prepare absolute output path
            abs_output_path = Path(output_path) / safe_protocol_name

            # Clean output directories
            self.clean_output_directories(abs_output_path)
            abs_output_path.mkdir(parents=True, exist_ok=True)

            # Load and process the CSV
            self.log(f"Loading CSV: {csv_file}")
            df = self.load_csv(csv_file, encoding)

            self.log(f"Processing {len(df)} rows into ReproSchema format")
            activities = self.process_dataframe(df)

            # Create activity schemas
            self.log(f"Creating {len(activities)} activity schemas")
            version = self.config.get("loris_version", "1.0.0")
            for activity_name, activity_data in activities.items():
                self.create_activity_schema(
                    activity_name,
                    activity_data,
                    abs_output_path,
                    version,
                )

            # Create protocol schema
            self.log("Creating protocol schema")
            self.create_protocol_schema(
                protocol_name,
                self.config,
                list(activities.keys()),
                abs_output_path,
            )

            # Final cleanup
            self.remove_ds_store(abs_output_path)

            # Update quality report statistics
            self.quality_report["source_file"] = csv_file
            self.quality_report["statistics"] = {
                "total_rows": len(df),
                "activities": len(activities),
                "items": sum(
                    len(data["items"]) for data in activities.values()
                ),
                "issues_fixed": len(self.quality_report["fixes_applied"]),
                "warnings": len(self.quality_report["warnings"]),
            }

            # Save quality report
            self.save_quality_report(abs_output_path)

            self.log("Conversion completed successfully.")
            self.log(f"Output written to: {abs_output_path}")
            self.log(
                f"Generated: 1 protocol, {len(activities)} activities, and {sum(len(data['items']) for data in activities.values())} items"
            )

            if self.quality_report["fixes_applied"]:
                self.log(
                    f"Applied {len(self.quality_report['fixes_applied'])} automatic fixes"
                )
            if self.quality_report["warnings"]:
                self.log(
                    f"Generated {len(self.quality_report['warnings'])} warnings"
                )

        except Exception as e:
            self.log(f"Error during conversion: {str(e)}", "ERROR")
            import traceback

            traceback.print_exc()
            raise


def loris2reproschema(
    csv_file: str,
    config_file: str,
    output_path: str,
    encoding: Optional[str] = None,
    analyze: bool = False,
    verbose: bool = False,
):
    """
    Converts LORIS CSV data to ReproSchema format.

    Args:
        csv_file (str): Path to the input CSV file.
        config_file (str): Path to the YAML configuration file.
        output_path (str): Path to the output directory.
        encoding (str, optional): Encoding for reading the CSV.
        analyze (bool): If True, analyze CSV and exit.
        verbose (bool): If True, enable verbose logging.
    """
    try:
        # Load configuration
        config = load_config(config_file)

        # Add command line args to config
        config["verbose"] = verbose

        # Create converter
        converter = ReproSchemaConverter(config)

        if analyze:
            # Just analyze the CSV and print suggestions
            print("Analyzing CSV file structure...")
            analysis = converter.analyze_csv(csv_file, encoding)
            print("\nCSV Analysis Results:")
            print(f"Columns found: {len(analysis.get('columns', []))}")
            print("\nSuggested column mappings:")
            for key, value in analysis.get("suggested_mappings", {}).items():
                print(f"  {key}: {value}")

            if "domain_analysis" in analysis:
                print("\nDomain column analysis:")
                for col, stats in analysis["domain_analysis"].items():
                    print(f"  {col}: {stats['unique_values']} unique values")
                    print("    Top values:")
                    for val, count in stats["top_values"].items():
                        print(f"      {val}: {count}")

            if "field_type_analysis" in analysis:
                print("\nField type analysis:")
                for col, stats in analysis["field_type_analysis"].items():
                    print(f"  {col}: {stats['unique_types']} unique types")
                    print("    Top types:")
                    for val, count in stats["top_types"].items():
                        print(f"      {val}: {count}")

            print(
                "\nAdd these mappings to your config file to improve conversion."
            )
            return

        # Run conversion
        converter.convert(csv_file, output_path, encoding)

    except Exception as e:
        print(f"Error: {str(e)}")
        raise e
