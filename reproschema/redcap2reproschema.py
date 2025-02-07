import os
import re
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from bs4 import BeautifulSoup

from .context_url import CONTEXTFILE_URL
from .jsonldutils import get_context_version
from .models import Activity, Item, Protocol, write_obj_jsonld

# All the mapping used in the code
SCHEMA_MAP = {
    "Variable / Field Name": "@id",  # column A
    # "Item Display Name": "prefLabel", # there is no column for this
    "Field Note": "description",
    # TODO: often "Field Annotation" has "@HIDDEN" and other markers
    # TODO: not sure if this can be every treated as description
    # "Field Annotation": "isVis",  # column R
    "Section Header": "preamble",  # column C (need double-check)
    "Field Label": "question",  # column E
    "Field Type": "inputType",  # column D
    "Allow": "allow",  # TODO: I don't see this column in the examples
    "Required Field?": "valueRequired",  # column M
    "Text Validation Min": "minValue",  # column I
    "Text Validation Max": "maxValue",  # column J
    "Choices, Calculations, OR Slider Labels": "choices",  # column F
    "Branching Logic (Show field only if...)": "visibility",  # column L
    "Custom Alignment": "customAlignment",  # column N
    # "Identifier?": "identifiable",  # column K # todo: should we remove the identifiers completely?
    "responseType": "@type",  # not sre what to do with it
}

INPUT_TYPE_MAP = {
    "calc": "number",
    "sql": "number",
    "yesno": "radio",
    "radio": "radio",
    "checkbox": "radio",
    "descriptive": "static",
    "dropdown": "select",
    "text": "text",
    "notes": "text",
    "file": "documentUpload",
    "slider": "slider",
}

# Map certain field types directly to xsd types
VALUE_TYPE_MAP = {
    "text": "xsd:string",
    "date_": "xsd:date",
    "date_mdy": "xsd:date",  # ?? new one TODO: not sure what to do with it, it's not xsd:date
    "datetime_seconds_mdy": "xsd:date",  # ?? new one TODO: not sure what to do with it, it's not xsd:date
    "date_ymd": "xsd:date",  # new one
    "date_dmy": "xsd:date",
    "datetime_": "xsd:dateTime",
    "datetime_ymd": "xsd:dateTime",
    "time_": "xsd:time",
    "email": "xsd:string",
    "phone": "xsd:string",
    "number": "xsd:decimal",  # new one (TODO: could be integer, but have no idea of knowing)
    "float": "xsd:decimal",  # new one
    "integer": "xsd:integer",  # new one
    "signature": "xsd: string",  # ?? new one
    "zipcode": "xsd: string",  # new one
    "autocomplete": "xsd: string",  # ?? new one
}

# TODO: removing for now, since it's not used
# TODO: inputType is treated separately,
# TODO: I don't see allow and shuffle in the redcap csv
# TODO: I don't know what to do with customAlignment
# UI_LIST = ["shuffle", "allow", "customAlignment"]
COMPUTE_LIST = ["calc", "sql"]  # field types that should be used as compute
# TODO:  minValue and max Value can be smteims str, ignored for now
RESPONSE_COND = ["minValue", "maxValue"]
ADDITIONAL_NOTES_LIST = ["Field Note", "Question Number (surveys only)"]


def clean_dict_nans(obj):
    """Remove NaN values from a dictionary."""
    if not isinstance(obj, dict):
        return obj
    return {k: v for k, v in obj.items() if pd.notna(v)}


# TODO: normalized condition should depend on the field type, e.g., for SQL
def normalize_condition(condition_str, field_type=None):
    """Normalize condition strings with specific handling for calc fields."""
    if condition_str is None or pd.isna(condition_str):
        return None

    # Handle boolean values
    if isinstance(condition_str, bool):
        return condition_str
    if isinstance(condition_str, str):
        if condition_str.lower() == "true":
            return True
        if condition_str.lower() == "false":
            return False

    # Convert to string if needed
    if not isinstance(condition_str, str):
        try:
            condition_str = str(condition_str)
        except:
            return None

    try:

        # Clean HTML
        condition_str = BeautifulSoup(condition_str, "html.parser").get_text()
        condition_str = condition_str.strip()

        if not condition_str:
            return None

        # Common operator normalizations for all types
        operator_replacements = [
            (r"\s*\+\s*", " + "),  # Normalize spacing around +
            (r"\s*-\s*", " - "),  # Normalize spacing around -
            (r"\s*\*\s*", " * "),  # Normalize spacing around *
            (r"\s*\/\s*", " / "),  # Normalize spacing around /
            (r"\s*\(\s*", "("),  # Remove spaces after opening parenthesis
            (r"\s*\)\s*", ")"),  # Remove spaces before closing parenthesis
            (r"\s*,\s*", ","),  # Normalize spaces around commas
            (r"\s+", " "),  # Normalize multiple spaces
        ]

        # Apply operator normalizations first
        for pattern, repl in operator_replacements:
            condition_str = re.sub(pattern, repl, condition_str)

        # Then apply type-specific replacements
        if field_type in ["sql", "calc"]:
            # For calc fields, just remove brackets from field references
            condition_str = re.sub(r"\[([^\]]+)\]", r"\1", condition_str)
        else:
            # For branching logic
            replacements = [
                (r"\(([0-9]*)\)", r"___\1"),
                (r"([^>|<])=", r"\1=="),
                (r"\[([^\]]*)\]", r"\1"),  # Remove brackets and extra spaces
                (r"\bor\b", "||"),
                (r"\band\b", "&&"),
                (r'"', "'"),
            ]
            for pattern, repl in replacements:
                condition_str = re.sub(pattern, repl, condition_str)

        result = condition_str.strip()
        return result

    except Exception as e:
        print(f"Error normalizing condition: {str(e)}")
        return None


def process_field_properties(data):
    """
    Process field properties from REDCap data dictionary to create a property object.

    This function extracts and processes field properties from a REDCap data dictionary row,
    handling variable names, visibility conditions, field annotations, required fields,
    and matrix group information.

    Args:
        data (dict): A dictionary containing field data from the REDCap data dictionary.
            Expected keys include:
            - "Variable / Field Name": The field's variable name
            - "Branching Logic (Show field only if...)": Conditional display logic
            - "Field Annotation": Special field annotations (e.g., @READONLY, @HIDDEN)
            - "Required Field?": Whether the field is required
            - "Matrix Group Name": Matrix group identifier
            - "Matrix Ranking?": Matrix ranking information

    Returns:
        dict: A property object containing processed field information with the following structure:
            {
                "variableName": str,  # The field's variable name
                "isAbout": str,       # Reference to the item (e.g., "items/variable_name")
                "isVis": str/bool,    # Visibility condition or False if hidden
                "valueRequired": bool, # Optional, present if field is required
                "matrixGroupName": str,# Optional, present if field is part of a matrix
                "matrixRanking": bool  # Optional, present if matrix has ranking
            }

    Examples:
        >>> data = {
        ...     "Variable / Field Name": "age",
        ...     "Required Field?": "y",
        ...     "Branching Logic (Show field only if...)": "[gender] = '1'"
        ... }
        >>> process_field_properties(data)
        {'variableName': 'age', 'isAbout': 'items/age', 'valueRequired': True, 'isVis': "gender == '1'"}
    """
    if not isinstance(data, dict):
        return {"variableName": "unknown", "isAbout": "items/unknown"}

    var_name = str(data.get("Variable / Field Name", "unknown")).strip()
    prop_obj = {"variableName": var_name, "isAbout": f"items/{var_name}"}

    # Handle required field consistently
    if data.get("Required Field?", "").strip().lower() == "y":
        prop_obj["valueRequired"] = True

    # Set isVis only when needed
    condition = data.get("Branching Logic (Show field only if...)")
    if pd.notna(condition):
        normalized = normalize_condition(condition)
        if normalized:
            prop_obj["isVis"] = normalized

    # Handle field annotations that affect visibility
    annotation = data.get("Field Annotation", "").strip().upper()
    if annotation:
        if (
            "@HIDDEN" in annotation
            or "@READONLY" in annotation
            or "@CALCTEXT" in annotation
        ):
            prop_obj["isVis"] = False

    field_type = data.get("Field Type", "").strip().lower()
    if field_type in ["calc", "sql"]:
        prop_obj["isVis"] = False

    matrix_group = data.get("Matrix Group Name")
    if pd.notna(matrix_group):
        prop_obj["matrixGroupName"] = str(matrix_group).strip()
        if pd.notna(data.get("Matrix Ranking?")):
            prop_obj["matrixRanking"] = data["Matrix Ranking?"]

    return prop_obj


def parse_field_type_and_value(field):
    """
    Parse field type and determine appropriate value type.

    Args:
        field: Dictionary containing field information

    Returns:
        tuple: (input_type, value_type)
    """
    try:
        # Get and validate field type
        field_type = field.get("Field Type", "")
        if pd.isna(field_type):
            field_type = ""
        field_type = str(field_type).strip().lower()

        # Validate field type
        if field_type and field_type not in INPUT_TYPE_MAP:
            raise ValueError(
                f"Field type '{field_type}' is not currently supported, "
                f"supported types are: {', '.join(INPUT_TYPE_MAP.keys())}"
            )

        input_type = INPUT_TYPE_MAP.get(field_type, "text")
        value_type = "xsd:string"  # Default value type

        # Get validation type
        validation_type = field.get(
            "Text Validation Type OR Show Slider Number"
        )
        if pd.notna(validation_type):
            validation_type = str(validation_type).strip().lower()

            if validation_type:
                if validation_type not in VALUE_TYPE_MAP:
                    raise ValueError(
                        f"Validation type '{validation_type}' is not supported, "
                        f"supported types are: {', '.join(VALUE_TYPE_MAP.keys())}"
                    )

                value_type = VALUE_TYPE_MAP[validation_type]

                # Adjust input type based on validation
                if validation_type == "integer" and field_type == "text":
                    input_type = "number"
                elif (
                    validation_type in ["float", "number"]
                    and field_type == "text"
                ):
                    input_type = "float"
                elif validation_type == "email" and field_type == "text":
                    input_type = "email"
                elif validation_type == "signature" and field_type == "text":
                    input_type = "sign"
                elif value_type == "xsd:date" and field_type == "text":
                    input_type = "date"

        elif field_type == "yesno":
            value_type = "xsd:boolean"
        elif field_type in COMPUTE_LIST:
            value_type = "xsd:integer"

        # Handle radio/select fields with choices
        if input_type in ["radio", "select", "slider"]:
            choices = field.get("Choices, Calculations, OR Slider Labels")
            if pd.notna(choices):
                _, value_types = process_choices(
                    choices, field.get("Variable / Field Name", "unknown")
                )
                if value_types:
                    value_type = value_types[
                        0
                    ]  # Use first value type if multiple exist

        return input_type, value_type

    except Exception as e:
        print(f"Error parsing field type: {str(e)}")
        return "text", "xsd:string"  # Return defaults on error


def process_choices(choices_str, field_name):
    """
    Process REDCap choice options into structured format.

    Args:
        choices_str: String containing choice options
        field_name: Field name for error reporting

    Returns:
        tuple: (choices list, value types list) or (None, None) if invalid
    """
    try:
        if pd.isna(choices_str) or not isinstance(choices_str, str):
            return None, None

        choices_str = choices_str.strip()
        if not choices_str:
            return None, None

        choices = []
        choices_value_type = set()

        # Split choices by pipe
        choice_items = [c.strip() for c in choices_str.split("|") if c.strip()]

        if len(choice_items) < 1:
            print(f"Warning: No valid choices found in {field_name}")
            return None, None

        for choice in choice_items:
            # Split on first comma only
            parts = choice.split(",", 1)
            if len(parts) < 2:
                print(
                    f"Warning: Invalid choice format '{choice}' in {field_name}"
                )
                continue

            value_part = parts[0].strip()
            label_part = parts[1].strip()

            if not label_part:
                print(
                    f"Warning: Empty label in choice '{choice}' in {field_name}"
                )
                continue

            # Determine value type and convert value
            try:
                # First try integer conversion
                if value_part == "0":
                    value = 0
                    value_type = "xsd:integer"
                elif value_part.isdigit() and value_part[0] == "0":
                    value = value_part
                    value_type = "xsd:string"
                else:
                    try:
                        value = int(value_part)
                        value_type = "xsd:integer"
                    except ValueError:
                        try:
                            value = float(value_part)
                            value_type = "xsd:decimal"
                        except ValueError:
                            value = value_part
                            value_type = "xsd:string"

                choices_value_type.add(value_type)

                # Create choice object
                parsed_label = parse_html(label_part)
                choice_obj = {
                    "name": (
                        parsed_label if parsed_label else {"en": label_part}
                    ),
                    "value": value,
                }
                choices.append(choice_obj)

            except (ValueError, TypeError) as e:
                print(
                    f"Warning: Error processing choice '{choice}' in {field_name}: {str(e)}"
                )
                continue

        if not choices:
            return None, None

        return choices, list(choices_value_type)

    except Exception as e:
        print(f"Error processing choices for {field_name}: {str(e)}")
        return None, None


def parse_html(input_string, default_language="en"):
    """
    Parse HTML content and extract language-specific text.

    Args:
        input_string: The HTML string to parse
        default_language: Default language code (default: "en")

    Returns:
        dict: Dictionary of language codes to text content, or None if invalid
    """
    try:
        if pd.isna(input_string):
            return None

        result = {}

        # Handle non-string input
        if not isinstance(input_string, str):
            try:
                input_string = str(input_string)
            except:
                return None

        # Clean input string
        input_string = input_string.strip()
        if not input_string:
            return None

        # Parse HTML
        soup = BeautifulSoup(input_string, "html.parser")

        # Find elements with lang attribute
        lang_elements = soup.find_all(True, {"lang": True})

        if lang_elements:
            # Process elements with language tags
            for element in lang_elements:
                lang = element.get("lang", default_language).lower()
                text = element.get_text(strip=False)
                if text:
                    result[lang] = text

            # If no text was extracted but elements exist, try getting default text
            if not result:
                text = soup.get_text(strip=False)
                if text:
                    result[default_language] = text
        else:
            # No language tags found, use default language
            text = soup.get_text(strip=False)
            if text:
                result[default_language] = text

        return result if result else None

    except Exception as e:
        print(f"Error parsing HTML: {str(e)}")
        # Try to return plain text if HTML parsing fails
        try:
            if isinstance(input_string, str) and input_string.strip():
                return {default_language: input_string.strip()}
        except:
            pass
        return None


def process_row(
    abs_folder_path,
    schema_context_url,
    form_name,
    field,
    add_preamble=True,
):
    """Process a row of the REDCap data and generate the jsonld file for the item."""
    item_id = field.get(
        "Variable / Field Name", ""
    )  # item_id should always be the Variable name in redcap
    rowData = {
        "category": "reproschema:Item",
        "id": item_id,
        "prefLabel": {"en": item_id},  # there is no prefLabel in REDCap
        # "description": {"en": f"{item_id} of {form_name}"},
    }

    field_type = field.get("Field Type")
    if pd.isna(field_type):
        field_type = ""
    input_type, value_type = parse_field_type_and_value(field)

    # Initialize ui object with common properties
    ui_obj = {"inputType": input_type}

    # Handle readonly status first - this affects UI behavior
    annotation = field.get("Field Annotation")
    if annotation is not None and not pd.isna(annotation):
        annotation = str(annotation).upper()
        if (
            "@READONLY" in annotation
            or "@HIDDEN" in annotation
            or "@CALCTEXT" in annotation
            or field_type in COMPUTE_LIST
        ):
            ui_obj["readonlyValue"] = True

    rowData["ui"] = ui_obj
    rowData["responseOptions"] = {"valueType": [value_type]}

    # Handle specific field type configurations
    if field_type == "yesno":
        rowData["responseOptions"]["choices"] = [
            {"name": {"en": "Yes"}, "value": 1},
            {"name": {"en": "No"}, "value": 0},
        ]
    elif field_type == "checkbox":
        rowData["responseOptions"]["multipleChoice"] = True

    for key, value in field.items():
        if pd.isna(value):
            continue
        schema_key = SCHEMA_MAP.get(key)
        if not schema_key:
            continue

        if schema_key in ["question", "description"]:
            parsed_value = parse_html(value)
            if parsed_value:
                rowData[schema_key] = parsed_value

        elif schema_key == "preamble" and add_preamble:
            parsed_value = parse_html(value)
            if parsed_value:
                rowData[schema_key] = parsed_value

        elif schema_key == "allow":
            ui_obj["allow"] = value.split(", ")

        # choices are only for some input_types
        elif schema_key == "choices" and input_type in [
            "radio",
            "select",
            "slider",
        ]:
            choices, choices_val_type_l = process_choices(
                value, field_name=field["Variable / Field Name"]
            )
            if choices is not None:
                if input_type == "slider":
                    rowData["responseOptions"].update(
                        {
                            "choices": choices,
                            "valueType": choices_val_type_l,
                            "minValue": 0,
                            "maxValue": 100,
                        }
                    )
                else:
                    rowData["responseOptions"].update(
                        {
                            "choices": choices,
                            "valueType": choices_val_type_l,
                        }
                    )
        # for now adding only for numerics, sometimes can be string or date.. TODO
        elif schema_key in RESPONSE_COND and value_type in [
            "xsd:integer",
            "xsd:decimal",
        ]:
            try:
                if value_type == "xsd:integer":
                    parsed_value = int(value)
                else:
                    parsed_value = float(value)
                rowData["responseOptions"][schema_key] = parsed_value
            except ValueError:
                print(f"Warning: Value {value} is not a valid {value_type}")
                continue

        # elif key == "Identifier?" and value:
        #     identifier_val = value.lower() == "y"
        #     rowData.update(
        #         {
        #             schema_map[key]: [
        #                 {"legalStandard": "unknown", "isIdentifier": identifier_val}
        #             ]
        #         }
        #     )

        elif key in ADDITIONAL_NOTES_LIST:
            value_str = str(value).strip()
            if value_str:
                notes_obj = {
                    "source": "redcap",
                    "column": key,
                    "value": f'"{value_str}"',
                }
                rowData.setdefault("additionalNotesObj", []).append(notes_obj)

    cleaned_data = clean_dict_nans(rowData)
    if not cleaned_data or "id" not in cleaned_data:
        raise ValueError(f"Missing required fields for item {item_id}")

    it = Item(**rowData)
    file_path_item = os.path.join(
        f"{abs_folder_path}",
        "activities",
        form_name,
        "items",
        item_id,
    )

    write_obj_jsonld(it, file_path_item, contextfile_url=schema_context_url)


# create activity
def create_form_schema(
    abs_folder_path,
    schema_context_url,
    redcap_version,
    form_name,
    activity_display_name,
    order,
    bl_list,
    matrix_list,
    compute_list,
    preamble=None,
):
    """
    Create the JSON-LD schema for an Activity.

    Args:
        abs_folder_path (str/Path): Path to the output directory
        schema_context_url (str): URL for the schema context
        redcap_version (str): Version of REDCap being used
        form_name (str): Name of the form
        activity_display_name (str): Display name for the activity
        order (list): List of items in order
        bl_list (list): List of branching logic properties
        matrix_list (list): List of matrix group properties
        compute_list (list): List of computation fields
        preamble (str, optional): Form preamble text
    """
    try:
        # Validate inputs
        if (
            pd.isna(form_name).any()
            if isinstance(form_name, pd.Series)
            else pd.isna(form_name)
        ):
            raise ValueError("Form name is required")

        # Set default activity display name if not provided
        if (
            pd.isna(activity_display_name).any()
            if isinstance(activity_display_name, pd.Series)
            else pd.isna(activity_display_name)
        ):
            activity_display_name = str(form_name).replace("_", " ").title()

        # Clean and validate order list
        clean_order = []
        if order is not None:
            if isinstance(order, (list, pd.Series, np.ndarray)):
                clean_order = [
                    str(item).strip()
                    for item in order
                    if not (isinstance(item, pd.Series) and item.isna().any())
                    and not pd.isna(item)
                ]
                clean_order = list(dict.fromkeys(clean_order))

        # Clean and validate bl_list
        clean_bl_list = []
        if bl_list is not None:
            if isinstance(bl_list, (list, pd.Series, np.ndarray)):
                clean_bl_list = [
                    prop
                    for prop in bl_list
                    if prop is not None and isinstance(prop, dict)
                ]

        # Initialize schema
        json_ld = {
            "category": "reproschema:Activity",
            "id": f"{form_name}_schema",
            "prefLabel": {"en": str(activity_display_name)},
            "schemaVersion": get_context_version(schema_context_url),
            "version": redcap_version,
            "ui": {
                "order": clean_order,
                "addProperties": clean_bl_list,
                "shuffle": False,
            },
        }

        # Process preamble if present
        if preamble is not None:
            if isinstance(preamble, pd.Series):
                if not preamble.isna().all():
                    parsed_preamble = parse_html(
                        preamble.iloc[0] if len(preamble) > 0 else None
                    )
                    if parsed_preamble:
                        json_ld["preamble"] = parsed_preamble
            elif not pd.isna(preamble):
                parsed_preamble = parse_html(preamble)
                if parsed_preamble:
                    json_ld["preamble"] = parsed_preamble

        # Process matrix info if present
        if matrix_list and len(matrix_list) > 0:
            json_ld["matrixInfo"] = matrix_list

        # Process compute list if present
        if compute_list and len(compute_list) > 0:
            json_ld["compute"] = compute_list

        # Create Activity object and write to file
        act = Activity(**json_ld)
        path = Path(abs_folder_path) / "activities" / str(form_name)
        path.mkdir(parents=True, exist_ok=True)

        write_obj_jsonld(
            act,
            path / f"{form_name}_schema",
            contextfile_url=schema_context_url,
        )

    except Exception as e:
        raise Exception(
            f"Error creating form schema for {form_name}: {str(e)}"
        )


def process_activities(activity_name, protocol_visibility_obj, protocol_order):
    # Set default visibility condition
    protocol_visibility_obj[activity_name] = True

    protocol_order.append(activity_name)


def create_protocol_schema(
    abs_folder_path,
    schema_context_url,
    redcap_version,
    protocol_name,
    protocol_display_name,
    protocol_description,
    protocol_order,
    protocol_visibility_obj,
):
    # Construct the protocol schema
    protocol_schema = {
        "category": "reproschema:Protocol",
        "id": f"{protocol_name}_schema",
        "prefLabel": {"en": protocol_display_name},
        # "altLabel": {"en": f"{protocol_name}_schema"}, todo: should we add this?
        "description": {"en": protocol_description},
        "schemaVersion": "1.0.0-rc4",
        "version": redcap_version,
        "ui": {
            "addProperties": [],
            "order": [],
            "shuffle": False,
        },
    }

    # Populate addProperties list
    for activity in protocol_order:
        full_path = f"../activities/{activity}/{activity}_schema"
        add_property = {
            "isAbout": full_path,
            "variableName": f"{activity}_schema",
            # Assuming activity name as prefLabel, update as needed
            "prefLabel": {"en": activity.replace("_", " ").title()},
            "isVis": protocol_visibility_obj.get(
                activity, True
            ),  # Default to True if not specified
        }
        protocol_schema["ui"]["addProperties"].append(add_property)
        # Add the full path to the order list
        protocol_schema["ui"]["order"].append(full_path)

    prot = Protocol(**protocol_schema)
    # Write the protocol schema to file
    protocol_dir = f"{abs_folder_path}/{protocol_name}"
    os.makedirs(protocol_dir, exist_ok=True)
    schema_file = f"{protocol_name}_schema"
    file_path = os.path.join(protocol_dir, schema_file)
    write_obj_jsonld(prot, file_path, contextfile_url=schema_context_url)
    print(f"Protocol schema created in {file_path}")


def process_csv(csv_file, abs_folder_path, protocol_name):
    datas = {}
    order = {}
    compute = {}

    # TODO: add languages

    try:
        df = pd.read_csv(csv_file, encoding="utf-8-sig")
        df.columns = df.columns.map(
            lambda x: x.strip().strip('"').lstrip("\ufeff")
        )

        required_columns = ["Form Name", "Variable / Field Name", "Field Type"]
        missing_columns = [
            col for col in required_columns if col not in df.columns
        ]
        if missing_columns:
            raise ValueError(
                f"Missing required columns: {', '.join(missing_columns)}"
            )

        # Initialize structures for each unique form
        unique_forms = df["Form Name"].dropna().unique()
        if len(unique_forms) == 0:
            raise ValueError("No valid form names found in the CSV")

        for form_name in unique_forms:
            form_name = str(form_name).strip()
            if not form_name:
                continue

            datas[form_name] = []
            order[form_name] = []
            compute[form_name] = []

            form_dir = (
                Path(abs_folder_path) / "activities" / form_name / "items"
            )
            form_dir.mkdir(parents=True, exist_ok=True)

        # TODO: should we bring back the language
        # if not languages:
        #    languages = parse_language_iso_codes(row["Field Label"])

        for idx, row in df.iterrows():
            form_name = row["Form Name"]
            field_name = row["Variable / Field Name"]

            # Skip rows with missing essential data
            if pd.isna(form_name) or pd.isna(field_name):
                print(
                    f"Warning: Skipping row {idx+2} with missing form name or field name"
                )
                continue

            form_name = str(form_name).strip()
            field_name = str(field_name).strip()

            # Convert row to dict and clean NaN values
            row_dict = {k: v for k, v in row.to_dict().items() if pd.notna(v)}
            if not row_dict:
                print(f"Warning: Skipping empty row {idx+2}")
                continue

            datas[form_name].append(row_dict)
            field_path = f"items/{field_name}"

            field_type = row_dict.get("Field Type", "").strip().lower()
            field_annotation = row_dict.get("Field Annotation", "")

            # Handle compute fields
            is_compute = False

            # Case 1: Field is calc type
            if field_type in COMPUTE_LIST:
                calc_value = row_dict.get(
                    "Choices, Calculations, OR Slider Labels", ""
                )
                if calc_value and str(calc_value).strip():
                    compute_expression = normalize_condition(
                        calc_value, field_type=field_type
                    )
                    if compute_expression:
                        is_compute = True
                        compute[form_name].append(
                            {
                                "variableName": field_name,
                                "jsExpression": compute_expression,
                            }
                        )
                    else:
                        print(
                            f"Warning: Could not normalize calc expression for {field_name}: {calc_value}"
                        )

            # Case 2: Field has @CALCTEXT
            elif (
                field_annotation
                and "@CALCTEXT" in str(field_annotation).upper()
            ):
                match = re.search(r"@CALCTEXT\((.*)\)", field_annotation)
                if match:
                    compute_expression = normalize_condition(match.group(1))
                    if compute_expression:
                        is_compute = True
                        compute[form_name].append(
                            {
                                "variableName": field_name,
                                "jsExpression": compute_expression,
                            }
                        )

            # Add to order list only if not a compute field
            if not is_compute:
                order[form_name].append(field_path)

        return datas, order, compute

    except Exception as e:
        print(f"Error processing CSV: {str(e)}")
        raise


# todo adding output path
def redcap2reproschema(
    csv_file, yaml_file, output_path, schema_context_url=None
):
    """
    Convert a REDCap data dictionary to Reproschema format.

    Args:
        csv_file (str/Path): Path to the REDCap CSV file
        yaml_file (str/Path): Path to the YAML configuration file
        output_path (str/Path): Path to the output directory
        schema_context_url (str, optional): URL for the schema context

    Raises:
        ValueError: If required files are missing or invalid
        FileNotFoundError: If input files cannot be found
        Exception: For other processing errors
    """
    try:
        # Validate input files exist
        csv_path = Path(csv_file)
        yaml_path = Path(yaml_file)
        output_dir = Path(output_path)

        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_file}")
        if not yaml_path.exists():
            raise FileNotFoundError(f"YAML file not found: {yaml_file}")

        # Read and validate YAML configuration
        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                protocol = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML file: {str(e)}")

        # Extract and validate protocol information
        protocol_name = protocol.get("protocol_name", "").strip()
        if not protocol_name:
            raise ValueError("Protocol name not specified in the YAML file")

        protocol_display_name = protocol.get(
            "protocol_display_name", protocol_name
        )
        protocol_description = protocol.get("protocol_description", "")
        redcap_version = protocol.get("redcap_version", "1.0.0")

        # Set up output directory
        protocol_name = protocol_name.replace(" ", "_")
        abs_folder_path = output_dir / protocol_name
        abs_folder_path.mkdir(parents=True, exist_ok=True)

        # Set schema context URL
        if schema_context_url is None:
            schema_context_url = CONTEXTFILE_URL

        # Process CSV file
        print(f"Processing CSV file: {csv_path}")
        datas, order, compute = process_csv(
            csv_path, abs_folder_path, protocol_name
        )

        if not datas:
            raise ValueError("No valid data found in CSV file")

        # Initialize protocol variables
        protocol_visibility_obj = {}
        protocol_order = []

        # Process each form
        for form_name, rows in datas.items():
            print(f"\nProcessing form: {form_name}")
            if not rows:
                print(f"Warning: Empty form {form_name}, skipping")
                continue

            # Initialize form-level collections
            bl_list = []
            matrix_list = []
            preambles_list = []

            # Process fields in the form
            for field in rows:
                # Validate field data
                if (
                    not isinstance(field, dict)
                    or "Variable / Field Name" not in field
                ):
                    print(
                        f"Warning: Invalid field data in form {form_name}, skipping"
                    )
                    continue

                # Process field properties
                field_properties = process_field_properties(field)
                if field_properties:
                    bl_list.append(field_properties)

                # Handle matrix groups
                matrix_group = field.get("Matrix Group Name")
                matrix_ranking = field.get("Matrix Ranking?")
                if pd.notna(matrix_group) or pd.notna(matrix_ranking):
                    matrix_info = {
                        "variableName": field["Variable / Field Name"],
                    }
                    if pd.notna(matrix_group):
                        matrix_info["matrixGroupName"] = matrix_group
                    if pd.notna(matrix_ranking):
                        matrix_info["matrixRanking"] = matrix_ranking
                    matrix_list.append(matrix_info)

                # Handle preambles (section headers)
                preamble = field.get("Section Header")
                if pd.notna(preamble):
                    preamble = str(preamble).strip()
                    if preamble:
                        preambles_list.append(preamble)

            # Determine preamble handling strategy
            unique_preambles = set(preambles_list)
            if len(unique_preambles) == 1:
                # Single preamble for the whole form
                preamble_act = preambles_list[0]
                preamble_itm = False
            elif len(unique_preambles) == 0:
                # No preambles
                preamble_act = None
                preamble_itm = False
            else:
                # Multiple preambles, handle at item level
                preamble_act = None
                preamble_itm = True

            # Get form display name
            activity_display_name = rows[0].get("Form Name", form_name)

            # Create form schema
            print(f"Creating schema for form: {form_name}")
            create_form_schema(
                abs_folder_path=abs_folder_path,
                schema_context_url=schema_context_url,
                redcap_version=redcap_version,
                form_name=form_name,
                activity_display_name=activity_display_name,
                order=order[form_name],
                bl_list=bl_list,
                matrix_list=matrix_list,
                compute_list=compute[form_name],
                preamble=preamble_act,  # Note: using correct parameter name
            )

            # Process individual items
            for field in rows:
                field_name = field["Variable / Field Name"]
                print(f"Processing field: {field_name}")
                process_row(
                    abs_folder_path=abs_folder_path,
                    schema_context_url=schema_context_url,
                    form_name=form_name,
                    field=field,
                    add_preamble=preamble_itm,  # Note: consistent parameter naming
                )

            # Process form-level activities
            print(f"Processing activities for form: {form_name}")
            process_activities(
                form_name, protocol_visibility_obj, protocol_order
            )

        # Create final protocol schema
        print("\nCreating protocol schema")
        create_protocol_schema(
            abs_folder_path=abs_folder_path,
            schema_context_url=schema_context_url,
            redcap_version=redcap_version,
            protocol_name=protocol_name,
            protocol_display_name=protocol_display_name,
            protocol_description=protocol_description,
            protocol_order=protocol_order,
            protocol_visibility_obj=protocol_visibility_obj,
        )

        print(
            f"\nConversion completed successfully. Output directory: {abs_folder_path}"
        )

    except Exception as e:
        raise Exception(f"Error during conversion: {str(e)}") from e
