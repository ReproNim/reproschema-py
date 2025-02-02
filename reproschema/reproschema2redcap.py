import csv
from pathlib import Path
import logging

import requests

from .context_url import CONTEXTFILE_URL
from .jsonldutils import _is_url, load_file
from .models import Activity, Item, Protocol, ResponseOption
from .utils import start_server, stop_server

logger = logging.getLogger(__name__)


def fetch_choices_from_url(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        if isinstance(data, list):
            choices = [
                list(item.values())[0]
                for item in data
                if isinstance(item, dict) and item
            ]
        elif isinstance(data, dict):
            choices = list(data.values())
        else:
            return ""

        # Format choices as 'code, description'
        formatted_choices = [
            f"{idx}, {choice}" for idx, choice in enumerate(choices)
        ]
        return " | ".join(formatted_choices)
    except Exception as e:
        print(f"Error fetching choices from {url}: {e}")
        return ""


def find_Ftype_and_colH(item, row_data, response_options):
    """
    Determine field type and column H value.
    
    Args:
        item: Item object containing UI information
        row_data: Dictionary to store field data
        response_options: Response options object
        
    Returns:
        dict: Updated row_data with field type and validation info
    """
    # Extract the input type from the item_json
    f_type = item.ui.inputType
    col_h = ""

    if f_type in ["text", "textarea", "email"]:
        f_type = "text"
    elif f_type in ["static", "save"]:
        f_type = "descriptive"
    elif f_type == "integer":
        f_type = "text"
        col_h = "integer"
    elif f_type == "number":
        f_type = "text"
        col_h = "integer"
    elif f_type == "float":
        f_type = "text"
        col_h = "float"
    elif f_type == "date":
        f_type = "text"
        col_h = "date_mdy"
    elif f_type == "select":
        multiple_choice = getattr(response_options, 'multipleChoice', False)
        logger.debug(f"Multiple choice setting for {item.id}: {multiple_choice}")
        f_type = "checkbox" if multiple_choice else "dropdown"
    elif f_type == "radio":
        if getattr(response_options, 'multipleChoice', False):
            f_type = "checkbox"
    elif f_type.startswith("select"):
        f_type = "radio"
        choices_url = getattr(response_options, 'choices', None)
        if choices_url and isinstance(choices_url, str):
            choices_data = fetch_choices_from_url(choices_url)
            if choices_data:
                row_data["choices"] = choices_data
    elif f_type.startswith(("audio", "video", "image", "document")):
        f_type = "file"
    else:
        f_type = "text"

    row_data["field_type"] = f_type.lower()
    if col_h:
        row_data["val_type_OR_slider"] = col_h.lower()

    return row_data


def process_item(
    item,
    item_properties,
    activity_name,
    activity_preamble,
    contextfile,
    http_kwargs,
    compute_item=False,
    compute_expr=None,
):
    """
    Process an item in JSON format and extract relevant information into a dictionary.
    Only includes non-empty/non-None values to match clean_dict_nans behavior.
    """
    if activity_name.endswith("_schema"):
        activity_name = activity_name[:-7]

    # Initialize with only required fields
    row_data = {
        "var_name": item.id,
        "activity": activity_name,
    }

    # Extract and add non-empty response option values
    if isinstance(item.responseOptions, str):
        resp = load_file(
            item.responseOptions,
            started=True,
            http_kwargs=http_kwargs,
            fixoldschema=True,
            compact=True,
            compact_context=contextfile,
        )
        del resp["@context"]
        if "ResponseOption" in resp["category"]:
            response_options = ResponseOption(**resp)
        else:
            raise Exception(
                f"Expected to have ResponseOption but got {resp['category']}"
            )
    else:
        response_options = item.responseOptions

    # Only add values if they exist
    if response_options:
        if response_options.minValue is not None:
            row_data["val_min"] = response_options.minValue
        if response_options.maxValue is not None:
            row_data["val_max"] = response_options.maxValue

        # Handle choices
        choices = response_options.choices
        if choices and not isinstance(choices, str):
            if isinstance(choices, list):
                # Handle the case where choices is a list
                item_choices = []
                for ch in choices:
                    if hasattr(ch, 'value') and ch.value is not None:
                        name = ch.name.get('en', '') if hasattr(ch, 'name') else ''
                        item_choices.append(f"{ch.value}, {name}")
                if item_choices:
                    row_data["choices"] = " | ".join(item_choices)

    # Add valueRequired if explicitly True
    if (
        item_properties
        and isinstance(item_properties, dict)  # Ensure it's a dictionary
        and item_properties.get("valueRequired") is True
    ):
        row_data["required"] = "y"

    var_name = str(item.id).split("/")[-1]  # Get the last part of the id path
    
    # Handle compute items
    if compute_item and compute_expr:
        logger.debug(f"Processing compute item: {var_name}")
        logger.debug(f"Compute expression: {compute_expr}")
        row_data["choices"] = compute_expr
        row_data["field_type"] = "calc"
        # For computed fields, we may need to set visibility to false by default
        if any(score_type in var_name for score_type in ["_score", "_total"]):
            row_data["isVis_logic"] = False
    else:
        # Use find_Ftype_and_colH but only add non-empty values
        field_info = find_Ftype_and_colH(item, {}, response_options)
        if field_info.get("field_type"):
            row_data["field_type"] = field_info["field_type"]
        if field_info.get("val_type_OR_slider"):
            row_data["val_type_OR_slider"] = field_info["val_type_OR_slider"]

    # Handle visibility
    if var_name.endswith("_total_score"):
        row_data["isVis_logic"] = False
    elif (
        item_properties 
        and isinstance(item_properties, dict)  # Ensure it's a dictionary
        and "isVis" in item_properties 
        and item_properties["isVis"] is not True
    ):
        row_data["isVis_logic"] = item_properties["isVis"]

    # Handle description
    if (
        hasattr(item, 'description')
        and isinstance(item.description, dict)
        and item.description.get("en")
    ):
        row_data["field_notes"] = item.description["en"]

    # Handle preamble
    if (
        hasattr(item, 'preamble')
        and isinstance(item.preamble, dict)
        and item.preamble.get("en")
    ):
        row_data["preamble"] = item.preamble["en"]
    elif activity_preamble:
        row_data["preamble"] = activity_preamble

    # Handle question/field label
    if compute_item:
        question = item.description
    else:
        question = item.question if hasattr(item, 'question') else None

    if isinstance(question, dict) and question.get("en"):
        row_data["field_label"] = question["en"]
    elif isinstance(question, str) and question:
        row_data["field_label"] = question

    return row_data


def get_csv_data(dir_path, contextfile, http_kwargs):
    csv_data = []

    for protocol_dir in dir_path.iterdir():
        if protocol_dir.is_dir():
            schema_file = next(protocol_dir.glob("*_schema"), None)
            if schema_file:
                parsed_protocol_json = load_file(
                    schema_file,
                    started=True,
                    http_kwargs=http_kwargs,
                    fixoldschema=True,
                    compact=True,
                    compact_context=contextfile,
                )

                del parsed_protocol_json["@context"]
                prot = Protocol(**parsed_protocol_json)

                activity_order = prot.ui.order
                for activity_path in activity_order:
                    if not _is_url(activity_path):
                        activity_path = protocol_dir / activity_path
                        
                    parsed_activity_json = load_file(
                        activity_path,
                        started=True,
                        http_kwargs=http_kwargs,
                        fixoldschema=True,
                        compact=True,
                        compact_context=contextfile,
                    )
                    del parsed_activity_json["@context"]
                    act = Activity(**parsed_activity_json)

                    # Get activity name
                    activity_name = act.id.split("/")[-1]
                    if activity_name.endswith("_schema.jsonld"):
                        activity_name = activity_name[:-12]
                    elif activity_name.endswith(".jsonld"):
                        activity_name = activity_name[:-7]

                    # Create a map of computed items
                    compute_map = {}
                    if hasattr(act, 'compute'):
                        compute_map = {
                            comp.variableName: comp.jsExpression 
                            for comp in act.compute
                        }

                    # Process each item defined in addProperties
                    for item_def in parsed_activity_json["ui"]["addProperties"]:
                        item_path = item_def["isAbout"]
                        var_name = item_def["variableName"]
                        
                        # Get the item file path
                        if not _is_url(item_path):
                            full_item_path = Path(activity_path).parent / item_path
                        else:
                            full_item_path = item_path

                        try:
                            item_json = load_file(
                                full_item_path,
                                started=True,
                                http_kwargs=http_kwargs,
                                fixoldschema=True,
                                compact=True,
                                compact_context=contextfile,
                            )
                            item_json.pop("@context", "")
                            item = Item(**item_json)

                            activity_preamble = (
                                act.preamble.get("en", "").strip()
                                if hasattr(act, "preamble")
                                else ""
                            )

                            # Check if this is a computed item
                            compute_expr = compute_map.get(var_name)
                            is_computed = compute_expr is not None

                            row_data = process_item(
                                item,
                                item_def,
                                activity_name,
                                activity_preamble,
                                contextfile,
                                http_kwargs,
                                is_computed,
                                compute_expr
                            )
                            csv_data.append(row_data)
                            
                        except Exception as e:
                            print(f"Error processing item {item_path} for activity {activity_name}")
                            print(f"Error details: {str(e)}")
                            continue

    return csv_data

def write_to_csv(csv_data, output_csv_filename):
    # REDCap-specific headers
    headers = [
        "Variable / Field Name",
        "Form Name",
        "Section Header",
        "Field Type",
        "Field Label",
        "Choices, Calculations, OR Slider Labels",
        "Field Note",
        "Text Validation Type OR Show Slider Number",
        "Text Validation Min",
        "Text Validation Max",
        "Identifier?",
        "Branching Logic (Show field only if...)",
        "Required Field?",
        "Custom Alignment",
        "Question Number (surveys only)",
        "Matrix Group Name",
        "Matrix Ranking?",
        "Field Annotation",
    ]

    # Writing to the CSV file
    with open(
        output_csv_filename, "w", newline="", encoding="utf-8"
    ) as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()

        for row in csv_data:
            redcap_row = {}

            # Handle var_name URL conversion
            var_name = row["var_name"]
            if _is_url(var_name):
                var_name = var_name.split("/")[-1].split(".")[0]
            redcap_row["Variable / Field Name"] = var_name

            # Handle form name
            activity_name = row["activity"]
            if activity_name.endswith("_schema"):
                activity_name = activity_name[:-7]
            redcap_row["Form Name"] = activity_name

            # Map remaining fields
            field_mappings = {
                "preamble": "Section Header",
                "field_type": "Field Type",
                "field_label": "Field Label",
                "choices": "Choices, Calculations, OR Slider Labels",
                "field_notes": "Field Note",
                "val_type_OR_slider": "Text Validation Type OR Show Slider Number",
                "val_min": "Text Validation Min",
                "val_max": "Text Validation Max",
                "required": "Required Field?",
                "isVis_logic": "Branching Logic (Show field only if...)",
                "field_annotation": "Field Annotation",
                "matrix_group": "Matrix Group Name",
                "matrix_ranking": "Matrix Ranking?",
            }

            # Add mapped fields only if they exist and aren't empty
            for src_key, dest_key in field_mappings.items():
                if (
                    src_key in row
                    and row[src_key] is not None
                    and row[src_key] != ""
                ):
                    # Special handling for visibility logic
                    if src_key == "isVis_logic":
                        if (
                            row[src_key] is not True
                        ):  # Only add if not default True
                            redcap_row[dest_key] = row[src_key]
                    # Special handling for required field
                    elif src_key == "required":
                        redcap_row[dest_key] = "y" if row[src_key] else "n"
                    # Special handling for field annotation
                    elif src_key == "field_annotation":
                        current_annotation = redcap_row.get(dest_key, "")
                        if current_annotation:
                            redcap_row[dest_key] = (
                                f"{current_annotation} {row[src_key]}"
                            )
                        else:
                            redcap_row[dest_key] = row[src_key]
                    else:
                        redcap_row[dest_key] = row[src_key]

            writer.writerow(redcap_row)

    print("The CSV file was written successfully")


def reproschema2redcap(input_dir_path, output_csv_filename):
    contextfile = CONTEXTFILE_URL  # todo, give an option
    http_kwargs = {}
    stop, port = start_server()
    http_kwargs["port"] = port
    try:
        csv_data = get_csv_data(input_dir_path, contextfile, http_kwargs)
    except:
        raise
    finally:
        stop_server(stop)
    write_to_csv(csv_data, output_csv_filename)
