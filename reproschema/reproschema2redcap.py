import csv
from pathlib import Path

import requests

from .context_url import CONTEXTFILE_URL
from .jsonldutils import _is_url, load_file
from .models import Activity, Item, Protocol, ResponseOption
from .utils import start_server, stop_server


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
        multiple_choice = response_options.multipleChoice
        print("mult", multiple_choice)
        f_type = "checkbox" if multiple_choice else "dropdown"
    elif f_type == "radio":
        if response_options.multipleChoice:
            f_type = "checkbox"
    elif f_type.startswith("select"):  # TODO: this should be reviewed
        # Adjusting for selectCountry, selectLanguage, selectState types
        f_type = "radio"
        choices_url = response_options.choices
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

    Args:
        item_json (dict): The JSON object representing the item.
        activity_name (str): The name of the activity.

    Returns:
        dict: A dictionary containing the extracted information.
    """
    if activity_name.endswith("_schema"):
        activity_name = activity_name[:-7]
    row_data = {
        "val_min": "",
        "val_max": "",
        "choices": "",
        "required": "",
        "field_notes": "",
        "var_name": "",
        "activity": activity_name,
        "field_label": "",
        "isVis_logic": "",
    }

    # Extract min and max values from response options, if available
    # loading additional files if responseOptions is an url
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
    row_data["val_min"] = response_options.minValue if response_options else ""
    row_data["val_max"] = response_options.maxValue if response_options else ""

    # 'choices' processing is now handled in 'find_Ftype_and_colH' if it's a URL
    choices = response_options.choices if response_options else ""
    if choices and not isinstance(choices, str):
        if isinstance(choices, list):
            item_choices = [
                f"{ch.value}, {ch.name.get('en', '')}" for ch in choices
            ]
            row_data["choices"] = " | ".join(item_choices)

    if item_properties.get("valueRequired", "") is True:
        row_data["required"] = "y"
    if "isVis" in item_properties and item_properties["isVis"] is not True:
        row_data["isVis_logic"] = item_properties["isVis"]
    row_data["field_notes"] = item.description.get("en", "")
    row_data["preamble"] = item.preamble.get("en", activity_preamble)
    row_data["var_name"] = item.id

    if compute_item:
        # for compute items there are no questions
        question = item.description
    else:
        question = item.question
    if isinstance(question, dict):
        row_data["field_label"] = question.get("en", "")
    elif isinstance(question, str):
        row_data["field_label"] = question

    if compute_item and compute_expr:
        row_data["choices"] = compute_expr
        row_data["field_type"] = "calc"
    else:
        # Call helper function to find field type and validation type (if any) and update row_data
        row_data = find_Ftype_and_colH(item, row_data, response_options)

    return row_data


def get_csv_data(dir_path, contextfile, http_kwargs):
    csv_data = []

    # Iterate over directories in dir_path
    for protocol_dir in dir_path.iterdir():
        if protocol_dir.is_dir():
            # Check for a _schema file in each directory
            schema_file = next(protocol_dir.glob("*_schema"), None)
            print(f"Found schema file: {schema_file}")
            if schema_file:
                # Process the found _schema file
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
                    items_properties = {
                        el["variableName"]: el
                        for el in parsed_activity_json["ui"]["addProperties"]
                    }
                    items_properties.update(
                        {
                            el["isAbout"]: el
                            for el in parsed_activity_json["ui"][
                                "addProperties"
                            ]
                        }
                    )

                    if parsed_activity_json:
                        item_order = [("ord", el) for el in act.ui.order]
                        item_calc = [("calc", el) for el in act.compute]

                        for tp, item in item_order + item_calc:
                            if tp == "calc":
                                js_expr = item.jsExpression
                                if item.variableName in items_properties:
                                    item = items_properties[item.variableName][
                                        "isAbout"
                                    ]
                                else:
                                    print(
                                        "WARNING: no item properties found for",
                                        item.variableName,
                                        activity_name,
                                    )
                                    continue
                                item_calc = True
                            else:
                                item_calc = False
                                js_expr = None
                            it_prop = items_properties.get(item)
                            if not _is_url(item):
                                item = Path(activity_path).parent / item
                            try:
                                item_json = load_file(
                                    item,
                                    started=True,
                                    http_kwargs=http_kwargs,
                                    fixoldschema=True,
                                    compact=True,
                                    compact_context=contextfile,
                                )
                            except Exception:
                                print(f"Error loading item: {item}")
                                continue
                            item_json.pop("@context", "")
                            itm = Item(**item_json)
                            activity_name = act.id.split("/")[-1].split(".")[0]
                            activity_preamble = act.preamble.get(
                                "en", ""
                            ).strip()
                            row_data = process_item(
                                itm,
                                it_prop,
                                activity_name,
                                activity_preamble,
                                contextfile,
                                http_kwargs,
                                item_calc,
                                js_expr,
                            )
                            csv_data.append(row_data)
                # Break after finding the first _schema file
                break
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
        "Field Note",  # TODO: is this description?
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

        # Map the data from your format to REDCap format
        redcap_data = []
        for row in csv_data:
            var_name = row["var_name"]
            if _is_url(var_name):
                var_name = var_name.split("/")[-1].split(".")[0]
            redcap_row = {
                "Variable / Field Name": var_name,
                "Form Name": row["activity"],
                "Section Header": row[
                    "preamble"
                ],  # Update this if your data includes section headers
                "Field Type": row["field_type"],
                "Field Label": row["field_label"],
                "Choices, Calculations, OR Slider Labels": row["choices"],
                "Field Note": row["field_notes"],
                "Text Validation Type OR Show Slider Number": row.get(
                    "val_type_OR_slider", ""
                ),
                "Required Field?": row["required"],
                "Text Validation Min": row["val_min"],
                "Text Validation Max": row["val_max"],
                "Branching Logic (Show field only if...)": row["isVis_logic"],
                # Add other fields as necessary based on your data
            }
            redcap_data.append(redcap_row)

        writer.writeheader()
        for row in redcap_data:
            writer.writerow(row)

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
