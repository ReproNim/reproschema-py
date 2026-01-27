import json
import re
from pathlib import Path
from typing import Any, Dict

import pandas as pd

from .context_url import CONTEXTFILE_URL
from .convertutils import (
    create_activity_schema,
    create_protocol_schema,
    normalize_condition,
    parse_html,
    read_check_yaml_config,
)
from .redcap_mappings import (
    ADDITIONAL_NOTES_LIST,
    COMPUTE_LIST,
    INPUT_TYPE_MAP,
    REDCAP_COLUMN_MAP,
    REDCAP_COLUMN_REQUIRED,
    RESPONSE_COND,
    get_value_type,
)


def process_input_value_types(
    input_type_rc, value_type_rc
) -> (str, str, dict):
    """
    Process input type and value type to determine the final input type and value type.

    Args:
        input_type_rc (str): Input type from redcap form
        value_type_rc (str): Value type from redcap form

    Returns:
        tuple: (input_type, value_type, additional_notes)
        input_type (str): Final input type for ReproSchema
        value_type (str): Final value type for ReproSchema
        additional_notes (dict): Additional notes about custom types, or None
    """
    additional_notes = None

    # If input type in redcap is set but not recognized, raise an error
    if input_type_rc not in INPUT_TYPE_MAP:
        raise ValueError(
            f"Input type '{input_type_rc}' from redcap is not currently supported, "
            f"supported types are: {', '.join(INPUT_TYPE_MAP.keys())}"
        )
    elif input_type_rc:
        input_type = INPUT_TYPE_MAP.get(input_type_rc)

    if value_type_rc:
        try:
            # Try to get standard value type
            value_type = get_value_type(value_type_rc)
        except ValueError:
            # If it fails, it's an unknown validation type
            print(
                f"Warning: Unrecognized validation type '{value_type_rc}', treating as string"
            )
            value_type = "xsd:string"
            additional_notes = {
                "source": "redcap",
                "column": "Text Validation Type OR Show Slider Number",
                "value": value_type_rc,
            }

        # Adjust input type based on validation
        if value_type == "xsd:date" and input_type_rc == "text":
            input_type = "date"
        elif value_type_rc == "integer" and input_type_rc == "text":
            input_type = "number"
        elif value_type_rc in ["float", "number"] and input_type_rc == "text":
            input_type = "float"
        elif value_type_rc == "email" and input_type_rc == "text":
            input_type = "email"
        elif value_type_rc == "signature" and input_type_rc == "text":
            input_type = "sign"

    elif input_type_rc == "yesno":
        value_type = "xsd:boolean"
    elif input_type_rc == "truefalse":
        value_type = "xsd:boolean"
    elif input_type_rc in COMPUTE_LIST:
        value_type = "xsd:integer"
    else:  # if no validation type is set, default to string
        value_type = "xsd:string"

    return input_type, value_type, additional_notes


def process_response_options(row, input_type_rc, value_type) -> Dict[str, Any]:
    """
    Process response options from the row and return a dictionary of response options

    Args:
        row (dict): Dictionary containing all fields from the redcap csv row
        input_type_rc (str): Input type from redcap form
        value_type (str): ReproSchema value type
    Returns:
        dict: Response options and additional notes if any
    """
    input_type = INPUT_TYPE_MAP[input_type_rc]
    # Default response options
    response_options = {"valueType": [value_type]}
    additional_notes = None

    # Handle specific input_type_rc that modify other properties
    if input_type_rc == "yesno":
        response_options["choices"] = [
            {"name": {"en": "Yes"}, "value": 1},
            {"name": {"en": "No"}, "value": 0},
        ]
    elif input_type_rc == "truefalse":
        response_options["choices"] = [
            {"name": {"en": "True"}, "value": 1},
            {"name": {"en": "False"}, "value": 0},
        ]
    elif input_type_rc == "checkbox":
        response_options["multipleChoice"] = True

    if row.get("choices") and input_type:
        # We're checking input_type (ReproSchema type) here
        if input_type in ["radio", "select", "slider", "text", "static"]:
            choices, choices_val_type_l = process_choices(
                row.get("choices"), item_name=row["item_name"]
            )
            if choices:
                # We're checking input_type_rc (REDCap type) here
                if input_type_rc == "descriptive":
                    print(
                        f"Info: Preserving choices for descriptive field {row['item_name']}"
                    )
                    # Store as additional notes instead of in response options
                    # Serialize the choices to a string to comply with additionalNotesObj model
                    additional_notes = {
                        "source": "redcap",
                        "column": "Choices, Calculations, OR Slider Labels (Descriptive Field)",
                        "value": json.dumps(
                            choices
                        ),  # Convert choices to a JSON string
                    }
                else:
                    # For normal input types, process choices normally
                    response_options.update(
                        {
                            "choices": choices,
                            "valueType": choices_val_type_l,
                        }
                    )
            if input_type == "slider":
                response_options.update(
                    {
                        "minValue": 0,
                        "maxValue": 100,
                    }
                )
        elif input_type_rc in COMPUTE_LIST:
            pass  # taken care below, it's not really choices
        else:
            print(
                f"Warning: Unexpected input type for choices in {row['item_name']}: input type {input_type} "
                f"(original in redcap: {input_type_rc}), values: {row.get('choices')}"
            )

    for key in RESPONSE_COND:
        if row.get(key) is not None and str(row.get(key)).strip():
            # Min/max validations only apply to numeric types
            if value_type not in ["xsd:integer", "xsd:decimal"]:
                print(
                    f"Warning: {key} is not supported for non-numeric type {value_type}. Skipping."
                )
                continue

            try:
                # Parse as float first to handle any numeric format
                raw_value = float(row[key])

                # If it's a whole number, store as integer for cleaner JSON
                # Otherwise, keep as float
                if raw_value.is_integer():
                    parsed_value = int(raw_value)
                else:
                    parsed_value = raw_value

                response_options[key] = parsed_value

            except ValueError:
                print(
                    f"Warning: Value '{row[key]}' for {key} is not a valid number"
                )
                continue

    return response_options, additional_notes


def process_choices(choices_str, item_name):
    # Handle NaN values from pandas (empty cells in CSV)
    import pandas as pd

    if pd.isna(choices_str) or not choices_str:
        return None, None

    if len(choices_str.split("|")) < 2:
        print(
            f"WARNING: {item_name}: I found only one option for choice: {choices_str}"
        )

    choices = []
    choices_value_type = set()

    # Split choices by pipe
    choice_items = [c.strip() for c in choices_str.split("|") if c.strip()]

    if len(choice_items) < 1:
        print(f"Warning: No valid choices found in {item_name}")
        return None, None

    for choice in choice_items:
        # Split on first comma only
        parts = choice.split(",", 1)
        if len(parts) < 2:
            print(f"Warning: Invalid choice format '{choice}' in {item_name}")
            parts = parts * 2  # assuming the same value as label

        value_part = parts[0].strip()
        label_part = parts[1].strip()

        if not label_part:
            print(f"Warning: Empty label in choice '{choice}' in {item_name}")
            continue

        # Determine value type and convert value
        if value_part == "0":
            value = 0
            value_type = "xsd:integer"
        elif (
            value_part.isdigit() and value_part[0] == "0"
        ):  # and not choices_value_type.union({"xsd:decimal", "xsd:integer"}):
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
        choice_obj = {
            "name": parse_html(label_part) or {"en": label_part},
            "value": value,
        }
        choices.append(choice_obj)
    # sorting to make sure the order is consistent
    choices_value_type = list(choices_value_type)
    choices_value_type.sort()
    return (choices, choices_value_type) if choices else (None, None)


def process_preamble(
    row, prior_preamble_info, input_type_rc
) -> (str, Dict[str, str]):
    """
    Function to get preamble information from the row and preamble from the previous row.
    The preamble will be propagated it if necessary.
    Args:
        row: Dictionary containing all fields from the redcap csv row
        prior_preamble_info: Dictionary containing preamble information from the previous row
        input_type_rc: Original input type from redcap form

    Returns:
        tuple: (item_preamble, preamble_info_propagate)
        item_preamble: Preamble text for the current item
        preamble_info_propagate: Dictionary containing preamble information to propagate to the next item
    """
    preamble, preamble_gr, preamble_ind = None, None, None
    # checking if preamble is set in the current row
    preamble_val = row.get("preamble")
    if pd.notna(preamble_val) and preamble_val and str(preamble_val).strip():
        preamble = parse_html(row["preamble"])
        # setting the preamble index to 0 for new preamble
        preamble_ind = 0
        # checking if a group is set in the current row
        matrix_group_val = row.get("matrixGroup")
        if (
            pd.notna(matrix_group_val)
            and matrix_group_val
            and str(matrix_group_val).strip()
        ):
            preamble_gr = str(matrix_group_val).strip()
        # if group is not set, and the item is a descriptive type, I use preamble only for this row, will not be propagated
        elif input_type_rc == "descriptive":
            preamble_ind = None
    # if there is no preamble in the current row, check if there is a preamble from the previous row to propagate
    elif prior_preamble_info and prior_preamble_info.get("preamble"):
        preamble_previous, preamble_gr_previous, preamble_ind_previous = [
            prior_preamble_info[key] for key in ["preamble", "group", "index"]
        ]
        # if there is no group set in the previous row, propagate the preamble
        if preamble_gr_previous is None:
            preamble = preamble_previous
            # sometimes the group is set in the row after the preamble, so check again for the group
            if preamble_ind_previous == 0:
                matrix_group_val = row.get("matrixGroup")
                if (
                    pd.notna(matrix_group_val)
                    and matrix_group_val
                    and str(matrix_group_val).strip()
                ):
                    preamble_gr = str(matrix_group_val).strip()
            preamble_ind = preamble_ind_previous + 1
        # if the preamble from the previous row is set to the specific group, the current row should be in the same group
        else:
            matrix_group_val = row.get("matrixGroup")
            if (
                pd.notna(matrix_group_val)
                and matrix_group_val
                and str(matrix_group_val).strip() == preamble_gr_previous
            ):
                preamble = preamble_previous
                preamble_gr = preamble_gr_previous
                preamble_ind = preamble_ind_previous + 1

    # setting the preamble used for the specific row/item
    if preamble:
        item_preamble = preamble
    else:
        item_preamble = None

    # setting preamble information to propagate to the next item
    if preamble and preamble_ind is not None:
        preamble_info_propagate = {
            "preamble": preamble,
            "group": preamble_gr,
            "index": preamble_ind,
        }
    else:
        preamble_info_propagate = None
    return item_preamble, preamble_info_propagate


def process_row(
    row: Dict[str, Any], prior_preamble_info=None
) -> (Dict[str, Any], Dict[str, str], Dict[str, Any], Dict[str, Any]):
    """
    Process a single row of the CSV and return structured data for an item,
    preamble information that can be propagated to the next item.
    It also collects information needed for activity schema.
    Args:
        row: Dictionary containing all fields from the redcap csv row
        prior_preamble_info: Dictionary containing preamble information from the previous row

    Returns:
        tuple: (item_data, preamble_info_propagate, compute, addProperties)
        item_data: Dictionary containing structured data for the item
        preamble_info_propagate: Dictionary containing preamble information to propagate to the next item
        compute: Dictionary containing compute information for the activity schema
        addProperties: Dictionary containing additional properties for the activity schema
    """
    # processing input type and value type that will be used by reproschema, and original one from redcap
    input_type_raw = row.get("inputType")
    input_type_rc = (
        str(input_type_raw).strip().lower() if pd.notna(input_type_raw) else ""
    )
    value_type_raw = row.get("validation")
    value_type_rc = (
        str(value_type_raw).strip().lower() if pd.notna(value_type_raw) else ""
    )
    if not input_type_rc:
        input_type_rc = "text"

    input_type, value_type, input_value_notes = process_input_value_types(
        input_type_rc, value_type_rc
    )
    item_data = {
        "category": "reproschema:Item",
        "id": row["item_name"],
        "prefLabel": {"en": row["item_name"]},
        "question": parse_html(row["question"]),
        "ui": {"inputType": input_type},
    }

    response_options, choices_notes = process_response_options(
        row, input_type_rc, value_type
    )
    item_data["responseOptions"] = response_options

    # setting readonly to true based on annotation and field type
    annotation = row.get("annotation")
    if pd.notna(annotation) and annotation:
        annotation = annotation.upper()
        if (
            "@READONLY" in annotation
            or "@HIDDEN" in annotation
            or "@CALCTEXT" in annotation
        ):
            item_data["ui"]["readonlyValue"] = True
    elif input_type_rc in COMPUTE_LIST + ["descriptive"]:
        item_data["ui"]["readonlyValue"] = True

    # adding information from all "unprocessed" columns to the additionalNotesObj
    for key_orig in ADDITIONAL_NOTES_LIST:
        key = REDCAP_COLUMN_MAP.get(key_orig)
        value = row.get(key)
        if pd.notna(value) and value:
            value_str = str(value).strip()
            if value_str:
                notes_obj = {
                    "source": "redcap",
                    "column": key_orig,
                    "value": value_str,
                }
                item_data.setdefault("additionalNotesObj", []).append(
                    notes_obj
                )

    # processing preamble
    item_preamble, preamble_info_propagate = process_preamble(
        row, prior_preamble_info, input_type_rc
    )
    if item_preamble:
        item_data["preamble"] = item_preamble

    # processing information needed for the activity schema
    # checking compute
    compute = None
    if input_type_rc in COMPUTE_LIST:
        condition = normalize_condition(row.get("choices"))
        compute = {"variableName": row["item_name"], "jsExpression": condition}
    annotation = row.get("annotation")
    if (
        pd.notna(annotation)
        and annotation
        and "@CALCTEXT" in annotation.upper()
    ):
        calc_text = annotation
        match = re.search(r"@CALCTEXT\((.*)\)", normalize_condition(calc_text))
        if match:
            js_expression = match.group(1)
            compute = {
                "variableName": row["item_name"],
                "jsExpression": js_expression,
            }
        else:
            print(
                f"Warning/Error: Invalid @CALCTEXT annotation in {row['item_name']}: {calc_text}"
            )
    # for compute items, we should use description instead of question
    if compute:
        item_data["description"] = item_data.pop("question")

    # setting default properties
    addProperties = {
        "variableName": item_data["id"],
        "isAbout": f"items/{item_data['id']}",
        "valueRequired": False,
        "isVis": True,
    }
    value_required = row.get("valueRequired")
    if pd.notna(value_required) and value_required:
        value_required_str = str(value_required).strip().lower()
        if value_required_str in ["y", "yes", "true"]:
            addProperties["valueRequired"] = True
        elif value_required_str not in ["n", "no", "false"]:
            print(
                f"Warning: Unexpected value for valueRequired in {row['item_name']}: {value_required}"
            )

    annotation = row.get("annotation")
    if (
        pd.notna(annotation)
        and annotation
        and (
            "@READONLY" in annotation.upper()
            or "@HIDDEN" in annotation.upper()
        )
    ):
        addProperties["isVis"] = False
    elif compute:
        addProperties["isVis"] = False
    else:
        visibility = row.get("visibility")
        if pd.notna(visibility) and visibility:
            addProperties["isVis"] = normalize_condition(visibility)

    # Add custom validation type note and choices notes if present
    if input_value_notes:
        item_data.setdefault("additionalNotesObj", []).append(
            input_value_notes
        )
    if choices_notes:
        item_data.setdefault("additionalNotesObj", []).append(choices_notes)

    return item_data, preamble_info_propagate, compute, addProperties


def process_csv(csv_file, encoding=None) -> (Dict[str, Any], list):
    """
    Process a REDCap CSV file and extract structured data for items and activities.

    Args:
        csv_file: Path to the REDCap CSV file
        encoding (str, optional): Specific encoding to use for the CSV file

    Returns:
        tuple: (activities, protocol_activities_order)
        activities: Dictionary containing activity data
        protocol_activities_order: List of activity names in order
    """
    if encoding:
        try:
            df = pd.read_csv(csv_file, encoding=encoding, low_memory=False)
            print(f"Using specified encoding: {encoding}")
        except UnicodeDecodeError:
            raise ValueError(
                f"Failed to read CSV with specified encoding: {encoding}"
            )
    else:
        # Try multiple encodings in order
        encodings = ["utf-8-sig", "latin-1", "windows-1252", "cp1252"]
        df = None

        for encoding in encodings:
            try:
                df = pd.read_csv(csv_file, encoding=encoding, low_memory=False)
                print(f"Successfully read CSV with {encoding} encoding")
                break
            except UnicodeDecodeError:
                print(
                    f"Failed to decode with {encoding}, trying next encoding..."
                )

        if df is None:
            raise ValueError(
                "Failed to read CSV file with any of the attempted encodings. "
                "Please check the file encoding or convert it to UTF-8."
            )

    df.columns = df.columns.map(lambda x: x.strip().strip('"'))
    df = df.astype(str).replace("nan", "")

    # Validate required columns
    missing_columns = set(REDCAP_COLUMN_REQUIRED) - set(df.columns)
    if missing_columns:
        raise ValueError(
            f"Missing required columns: {', '.join(missing_columns)}"
        )
    different_columns = set(df.columns) - set(REDCAP_COLUMN_MAP.keys())
    if different_columns:
        print(
            "Warning: Found columns that are not in the mapping: ",
            different_columns,
        )

    df = df.rename(columns=REDCAP_COLUMN_MAP)
    activities = {}
    prot_actvities_order = []
    for activity_name, group in df.groupby("activity_name", sort=False):
        if not activity_name:
            print("WARNING: Some rows in CSV have no activity name, skipping")
            continue
        items = []
        item_preamble_info = None
        act_addProperties = []
        act_items_order = []
        act_compute = []
        act_preamble = []
        for row in group.to_dict("records"):
            item, item_preamble_info, compute, addProperty = process_row(
                row, prior_preamble_info=item_preamble_info
            )
            items.append(item)
            act_addProperties.append(addProperty)
            if compute:
                act_compute.append(compute)
            else:
                act_items_order.append(f"items/{item['id']}")
                if item.get("preamble"):
                    act_preamble.append(item["preamble"]["en"])

        activities[activity_name] = {
            "items": items,
            "order": act_items_order,
            "compute": act_compute,
            "addProperties": act_addProperties,
        }
        prot_actvities_order.append(activity_name)
        # checking if all preamble the same for all questions
        # if they are, it should be treated as an activity preamble
        act_compute_name = [c["variableName"] for c in act_compute]
        if (
            act_preamble
            and len(set(act_preamble)) == 1
            and len(act_preamble) == len(act_items_order)
        ):
            activities[activity_name]["preamble"] = {"en": act_preamble[0]}
            for item in items:
                # I was checking only for questions to see if this can be treated as an activity preamble,
                # but if there is a preamble also for compute item it should be removed
                if item["id"] in act_compute_name:
                    if item.get("preamble") == {"en": act_preamble[0]}:
                        del item["preamble"]
                else:
                    del item["preamble"]

    return activities, prot_actvities_order


def redcap2reproschema(
    csv_file, yaml_file, output_path, schema_context_url=None, encoding=None
):
    """
    Convert a REDCap data dictionary to Reproschema format.

    Args:
        csv_file (str/Path): Path to the REDCap CSV file
        yaml_file (str/Path): Path to the YAML configuration file
        output_path (str/Path): Path to the output directory
        schema_context_url (str, optional): URL for the schema context
        encoding (str, optional): Specific encoding to use for the CSV file

    Raises:
        ValueError: If required files are missing or invalid
        FileNotFoundError: If input files cannot be found
        Exception: For other processing errors
    """

    # Validate input files exist
    csv_path = Path(csv_file)
    yaml_path = Path(yaml_file)
    output_dir = Path(output_path)

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_file}")
    if not yaml_path.exists():
        raise FileNotFoundError(f"YAML file not found: {yaml_file}")

    protocol = read_check_yaml_config(yaml_path)
    protocol_name = protocol.get("protocol_name").replace(" ", "_")
    # Set up output directory
    abs_folder_path = output_dir / protocol_name
    abs_folder_path.mkdir(parents=True, exist_ok=True)

    # Set schema context URL
    if schema_context_url is None:
        schema_context_url = CONTEXTFILE_URL

    # Process the CSV file with the specified encoding
    activities, prot_activities_order = process_csv(csv_path, encoding)

    for activity_name, activity_data in activities.items():
        create_activity_schema(
            activity_name,
            activity_data,
            abs_folder_path,
            protocol.get("redcap_version"),
            schema_context_url,
        )

    # Create protocol schema
    create_protocol_schema(
        protocol, prot_activities_order, abs_folder_path, schema_context_url
    )
    print("OUTPUT DIRECTORY: ", abs_folder_path)
