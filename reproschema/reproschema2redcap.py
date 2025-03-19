import csv
import logging
from pathlib import Path

import requests

from .context_url import CONTEXTFILE_URL
from .jsonldutils import _is_url, load_file
from .models import Activity, Item, Protocol, ResponseOption
from .redcap_mappings import REDCAP_COLUMN_MAP, REDCAP_COLUMN_MAP_REVERSE
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


def find_input_type_value_type_rc(item, response_options):
    """
    Determine input type and value type that should be in RedCap

    Args:
        item: Item object containing UI information
        response_options: Response options object

    Returns:
        dict: Updated row_data with field type and validation info
    """
    # Extract the input type from the item_json
    input_type = item.ui.inputType
    value_type_rc = ""

    if "text" in input_type:
        input_type_rc = "text"
    elif input_type in ["static", "save"]:
        input_type_rc = "descriptive"
    elif input_type == "number":
        input_type_rc = "text"
        value_type_rc = "integer"
    elif input_type == "float":
        input_type_rc = "text"
        value_type_rc = "float"
    elif input_type == "date":
        input_type_rc = "text"
        value_type_rc = "date_mdy"  # TODO: redcap has more types
    elif input_type.startswith("select"):
        input_type_rc = "dropdown"
    elif input_type == "radio":
        if getattr(response_options, "multipleChoice", False):
            input_type_rc = "checkbox"
        else:
            input_type_rc = "radio"  # todo: should add yes, no?
    elif input_type.startswith(("audio", "video", "image", "document")):
        input_type_rc = "file"
    else:
        print(f"Warning: Unknown input type: {input_type}, defaulting to text")
        input_type_rc = "text"

    info_rc = {"inputType": input_type_rc.lower()}
    if value_type_rc:
        info_rc["validation"] = value_type_rc.lower()

    return info_rc


def process_item(
    item,
    item_properties,
    activity_name,
    activity_preamble,
    contextfile,
    http_kwargs,
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
            row_data["minValue"] = response_options.minValue
        if response_options.maxValue is not None:
            row_data["maxValue"] = response_options.maxValue

        # Handle choices
        choices = response_options.choices
        if choices:
            if isinstance(choices, str):
                choices_data = fetch_choices_from_url(choices)
                if choices_data:
                    row_data["choices"] = choices_data
            elif isinstance(choices, list):
                # Handle the case where choices is a list
                item_choices = []
                for ch in choices:
                    if hasattr(ch, "value") and ch.value is not None:
                        name = (
                            ch.name.get("en", "")
                            if hasattr(ch, "name")
                            else ""
                        )
                        item_choices.append(f"{ch.value}, {name}")
                if item_choices:
                    row_data["choices"] = " | ".join(item_choices)
            else:
                raise Exception(
                    f"Choices should be a string or list, got {choices}"
                )

    # Add valueRequired if explicitly True
    if (
        item_properties
        and isinstance(item_properties, dict)  # Ensure it's a dictionary
        and item_properties.get("valueRequired") is True
    ):
        row_data["valueRequired"] = "y"

    var_name = str(item.id).split("/")[-1]  # Get the last part of the id path

    # Handle compute items
    if compute_expr:
        logger.debug(f"Processing compute item: {var_name}")
        logger.debug(f"Compute expression: {compute_expr}")
        row_data["choices"] = compute_expr
        row_data["inputType"] = "calc"  # todo: we don't have sql
        row_data["visibility"] = False
    else:
        field_info = find_input_type_value_type_rc(item, response_options)
        row_data["inputType"] = field_info["inputType"]
        if field_info.get("validation"):
            row_data["validation"] = field_info["validation"]

    if (
        item_properties
        and isinstance(item_properties, dict)  # Ensure it's a dictionary
        and "isVis" in item_properties
        and item_properties["isVis"] is not True
    ):
        row_data["visibility"] = item_properties["isVis"]

    # Handle preamble
    if (
        hasattr(item, "preamble")
        and isinstance(item.preamble, dict)
        and item.preamble.get("en")
    ):
        row_data["preamble"] = item.preamble["en"]
    elif activity_preamble:
        row_data["preamble"] = activity_preamble

    # Handle question/field label
    if compute_expr:
        question = item.description
    else:
        question = item.question if hasattr(item, "question") else None

    if isinstance(question, dict) and question.get("en"):
        row_data["question"] = question["en"]
    elif isinstance(question, str) and question:
        row_data["question"] = question

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
                    act_data = process_activity(
                        activity_path, contextfile, http_kwargs
                    )
                    csv_data += act_data
    return csv_data


def process_activity(activity_path, contextfile, http_kwargs):
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
    if hasattr(act, "compute"):
        compute_map = {
            comp.variableName: comp.jsExpression for comp in act.compute
        }
    act_data = []
    var_name_list = []
    # Process each item defined in addProperties
    for item_def in parsed_activity_json["ui"]["addProperties"]:
        item_path = item_def["isAbout"]
        var_name = item_def["variableName"]
        if var_name in var_name_list:
            continue
        else:
            var_name_list.append(var_name)
        # Get the item file path
        if not _is_url(item_path):
            full_item_path = Path(activity_path).parent / item_path
        else:
            full_item_path = item_path

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

        row_data = process_item(
            item,
            item_def,
            activity_name,
            activity_preamble,
            contextfile,
            http_kwargs,
            compute_expr,
        )
        act_data.append(row_data)
    return act_data


def write_to_csv(csv_data, output_csv_filename):
    headers = list(REDCAP_COLUMN_MAP.keys())
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

            # Add mapped fields only if they exist and aren't empty
            for src_key, dest_key in REDCAP_COLUMN_MAP_REVERSE.items():
                if (
                    src_key in row
                    and row[src_key] is not None
                    and row[src_key] != ""
                ):
                    # Special handling for visibility logic
                    if src_key == "visibility":
                        if (
                            row[src_key] is not True
                        ):  # Only add if not default True
                            redcap_row[dest_key] = row[src_key]
                    # Special handling for required field
                    elif src_key == "valueRequired":
                        redcap_row[dest_key] = "y" if row[src_key] else "n"
                    # Special handling for field annotation
                    elif src_key == "annotation":
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
