"""
Convert OpenDataCapture (ODC) form instrument to ReproSchema format.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .context_url import CONTEXTFILE_URL
from .convertutils import (
    create_activity_schema,
    create_protocol_schema,
    parse_html,
)
from .odc_mappings import (
    get_odc_input_type,
    get_odc_value_type,
    is_multiple_choice,
)

logger = logging.getLogger(__name__)


def load_odc_instrument(file_path: Path) -> Dict[str, Any]:
    """
    Load ODC instrument from JSON file.

    Args:
        file_path: Path to the ODC JSON file

    Returns:
        Dictionary containing the ODC instrument data
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("ODC instrument must be a JSON object")
            return data
    except FileNotFoundError:
        raise FileNotFoundError(f"ODC instrument file not found: {file_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in ODC instrument file: {str(e)}")


def process_options(
    options: Dict[str, Any], value_type: str
) -> List[Dict[str, Any]]:
    """
    Convert ODC options to ReproSchema choices.

    Args:
        options: ODC options dictionary
        value_type: XSD value type

    Returns:
        List of ReproSchema choices
    """
    choices = []
    if not options or not isinstance(options, dict):
        return choices

    for val, label in options.items():
        # Convert value to appropriate type
        processed_val = val
        if "integer" in value_type:
            try:
                processed_val = int(val)
            except ValueError:
                logger.warning(
                    "Could not convert option value '%s' to integer, "
                    "using string fallback",
                    str(val),
                )
                processed_val = str(val)
        elif "decimal" in value_type or "float" in value_type:
            try:
                processed_val = float(val)
            except ValueError:
                logger.warning(
                    "Could not convert option value '%s' to float, "
                    "using string fallback",
                    str(val),
                )
                processed_val = str(val)

        choices.append({"name": {"en": str(label)}, "value": processed_val})

    return choices


def process_field(
    name: str, field_data: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Process a single ODC field and return one or more ReproSchema items.

    Args:
        name: Field name
        field_data: ODC field data

    Returns:
        List of ReproSchema item dictionaries
    """
    # Normalize kind and variant
    kind = field_data.get("kind", "string").lower().strip()
    variant = (field_data.get("variant") or "").lower().strip() or None

    # Handle special complex fields
    if kind == "record-array":
        return process_record_array(name, field_data)
    if kind == "number-record" and variant == "likert":
        return process_likert(name, field_data)
    if kind == "dynamic":
        logger.warning(
            "Skipping dynamic field '%s': dynamic rendering not supported",
            name,
        )
        return []

    # Simple field processing
    input_type = get_odc_input_type(kind, variant)
    value_type = get_odc_value_type(kind)

    item = {
        "category": "reproschema:Item",
        "id": name,
        "prefLabel": {"en": name},
        "ui": {"inputType": input_type},
        "responseOptions": {"valueType": [value_type]},
    }

    # Add question/label
    label = field_data.get("label")
    if label:
        item["question"] = {"en": str(parse_html(label))}

    # Add description/hint
    description = field_data.get("description")
    if description:
        item["description"] = {"en": str(parse_html(description))}

    # Add choices if applicable
    options = field_data.get("options")
    if options:
        item["responseOptions"]["choices"] = process_options(
            options, value_type
        )

    # Handle multiple choice
    if is_multiple_choice(kind, variant):
        item["responseOptions"]["multipleChoice"] = True

    # Handle min/max for numbers
    if kind == "number":
        if "min" in field_data:
            item["responseOptions"]["minValue"] = field_data["min"]
        if "max" in field_data:
            item["responseOptions"]["maxValue"] = field_data["max"]

    # Add metadata to additionalNotesObj
    notes = [
        {"source": "odc", "column": "kind", "value": kind},
        {"source": "odc", "column": "variant", "value": variant},
    ]
    item["additionalNotesObj"] = notes

    return [item]


def process_record_array(
    name: str, field_data: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Process an ODC record-array field into prefixed items.

    Args:
        name: Field name
        field_data: ODC field data

    Returns:
        List of ReproSchema items
    """
    items = []
    fieldset = field_data.get("fieldset", {})
    if not fieldset or not isinstance(fieldset, dict):
        return items

    for sub_name, sub_field in fieldset.items():
        prefixed_name = f"{name}_{sub_name}"
        sub_items = process_field(prefixed_name, sub_field)
        for item in sub_items:
            item.setdefault("additionalNotesObj", []).append(
                {
                    "source": "odc",
                    "column": "record-array-parent",
                    "value": name,
                }
            )
            items.append(item)

    return items


def process_likert(
    name: str, field_data: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Process an ODC likert field into multiple items (one per row).

    Args:
        name: Field name
        field_data: ODC field data

    Returns:
        List of ReproSchema items
    """
    items = []
    rows = field_data.get("items", {})
    options = field_data.get("options", {})

    if not rows or not isinstance(rows, dict):
        return items

    for row_name, row_data in rows.items():
        prefixed_name = f"{name}_{row_name}"
        row_label = row_data.get("label", row_name)

        item = {
            "category": "reproschema:Item",
            "id": prefixed_name,
            "prefLabel": {"en": prefixed_name},
            "question": {"en": str(row_label)},
            "ui": {"inputType": "radio"},
            "responseOptions": {
                "valueType": ["xsd:integer"],
                "choices": process_options(options, "xsd:integer"),
            },
        }

        item["additionalNotesObj"] = [
            {"source": "odc", "column": "likert-parent", "value": name},
            {"source": "odc", "column": "kind", "value": "number-record"},
            {"source": "odc", "column": "variant", "value": "likert"},
        ]
        items.append(item)

    return items


def odc2reproschema(
    input_file: str,
    output_path: str = ".",
    instrument_name: Optional[str] = None,
    schema_context_url: Optional[str] = None,
):
    """
    Convert ODC form instrument to ReproSchema format.

    Args:
        input_file: Path to ODC JSON file
        output_path: Path to output directory
        instrument_name: Override instrument name
        schema_context_url: URL for schema context (optional)
    """
    input_path = Path(input_file)
    output_dir = Path(output_path)

    # Load instrument
    data = load_odc_instrument(input_path)

    # Get metadata
    details = data.get("details", {})
    internal = data.get("internal", {})

    name = instrument_name or internal.get("name") or input_path.stem
    name = name.strip().replace(" ", "_")
    title = details.get("title") or name
    description = details.get("description") or ""
    version = str(internal.get("edition", "1"))

    # Process content
    content = data.get("content", {})
    if not isinstance(content, dict):
        raise ValueError(
            f"ODC instrument 'content' must be a dictionary, "
            f"got {type(content).__name__}"
        )

    all_items = []
    items_order = []
    add_properties = []

    for field_name, field_data in content.items():
        processed_items = process_field(field_name, field_data)
        for item in processed_items:
            all_items.append(item)
            items_order.append(f"items/{item['id']}")
            add_properties.append(
                {
                    "variableName": item["id"],
                    "isAbout": f"items/{item['id']}",
                    "isVis": True,
                }
            )

    # Prepare activity data
    activity_data = {
        "items": all_items,
        "order": items_order,
        "addProperties": add_properties,
        "compute": [],  # TODO: Handle measures
        "label": title,
        "description": description,
    }

    # Set up output directory
    abs_folder_path = output_dir / name
    abs_folder_path.mkdir(parents=True, exist_ok=True)

    # Set schema context URL
    if schema_context_url is None:
        schema_context_url = CONTEXTFILE_URL

    # Create activity schema
    create_activity_schema(
        name, activity_data, abs_folder_path, version, schema_context_url
    )

    # Create dummy protocol info for create_protocol_schema
    protocol_info = {
        "protocol_name": name,
        "protocol_display_name": title,
        "protocol_description": description,
        "source_version": version,
    }

    create_protocol_schema(
        protocol_info, [name], abs_folder_path, schema_context_url
    )

    logger.info("Conversion complete. Output: %s", abs_folder_path)
    return abs_folder_path
