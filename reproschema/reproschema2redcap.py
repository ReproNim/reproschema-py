import sys
import json
import csv
from pathlib import Path
import requests
from pyld import jsonld

from .models import (
    Item,
    Activity,
    Protocol,
    ResponseOption,
    ResponseActivity,
    Response,
    write_obj_jsonld,
)
from .utils import fixing_old_schema, start_server, stop_server
from .jsonldutils import load_file


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
        formatted_choices = [f"{idx}, {choice}" for idx, choice in enumerate(choices)]
        return " | ".join(formatted_choices)
    except Exception as e:
        print(f"Error fetching choices from {url}: {e}")
        return ""


def find_Ftype_and_colH(item, row_data):
    # Extract the input type from the item_json
    f_type = item.ui.inputType
    col_h = ""

    if f_type in ["text", "textarea", "email"]:
        f_type = "text"
    elif f_type == "integer":
        f_type = "text"
        col_h = "integer"
    elif f_type in ["number", "float"]:
        f_type = "text"
        col_h = "number"
    elif f_type == "date":
        f_type = "text"
        col_h = "date_mdy"
    elif f_type == "select":
        multiple_choice = item.responseOptions.multipleChoice
        print("mult", multiple_choice)
        f_type = "checkbox" if multiple_choice else "dropdown"
    elif f_type.startswith("select"):
        # Adjusting for selectCountry, selectLanguage, selectState types
        f_type = "radio"
        choices_url = item.responseOptions.choices
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


def process_item(item, activity_name):
    """
    Process an item in JSON format and extract relevant information into a dictionary.

    Args:
        item_json (dict): The JSON object representing the item.
        activity_name (str): The name of the activity.

    Returns:
        dict: A dictionary containing the extracted information.
    """
    row_data = {
        "val_min": "",
        "val_max": "",
        "choices": "",
        "required": "",
        "field_notes": "",
        "var_name": "",
        "activity": activity_name.lower(),
        "field_label": "",
    }

    # Extract min and max values from response options, if available
    response_options = item.responseOptions
    row_data["val_min"] = response_options.minValue
    row_data["val_max"] = response_options.maxValue

    # 'choices' processing is now handled in 'find_Ftype_and_colH' if it's a URL
    choices = response_options.choices
    if choices and not isinstance(choices, str):
        if isinstance(choices, list):
            item_choices = [f"{ch.value}, {ch.name.get('en', '')}" for ch in choices]
            row_data["choices"] = " | ".join(item_choices)

    row_data["required"] = ""  # response_options.get("requiredValue", "")
    row_data["field_notes"] = item.altLabel.get("en", "")
    row_data["var_name"] = item.id

    question = item.question
    if isinstance(question, dict):
        row_data["field_label"] = question.get("en", "")
    elif isinstance(question, str):
        row_data["field_label"] = question

    # Call helper function to find field type and validation type (if any) and update row_data
    row_data = find_Ftype_and_colH(item, row_data)

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
                for relative_activity_path in activity_order:
                    activity_path = protocol_dir / relative_activity_path
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

                    if parsed_activity_json:
                        item_order = act.ui.order
                        for item in item_order:
                            item_path = activity_path.parent / item
                            item_json = load_file(
                                item_path,
                                started=True,
                                http_kwargs=http_kwargs,
                                fixoldschema=True,
                                compact=True,
                                compact_context=contextfile,
                            )
                            del item_json["@context"]
                            itm = Item(**item_json)
                            if item_json:
                                row_data = process_item(itm, activity_path.stem)
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
    with open(output_csv_filename, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)

        # Map the data from your format to REDCap format
        redcap_data = []
        for row in csv_data:
            redcap_row = {
                "Variable / Field Name": row["var_name"],
                "Form Name": row["activity"],
                "Section Header": "",  # Update this if your data includes section headers
                "Field Type": row["field_type"],
                "Field Label": row["field_label"],
                "Choices, Calculations, OR Slider Labels": row["choices"],
                "Field Note": row["field_notes"],
                "Text Validation Type OR Show Slider Number": row.get(
                    "val_type_OR_slider", ""
                ),
                "Text Validation Min": row["val_min"],
                "Text Validation Max": row["val_max"],
                # Add other fields as necessary based on your data
            }
            redcap_data.append(redcap_row)

        writer.writeheader()
        for row in redcap_data:
            writer.writerow(row)

    print("The CSV file was written successfully")


def main(input_dir_path, output_csv_filename):
    contextfile = (
        Path(__file__).resolve().parent / "models/reproschema"
    )  # todo, give an option
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


if __name__ == "__main__":
    # check if input_dir_path and output_csv_filename are provided
    if len(sys.argv) < 3:
        print(
            "Usage: python reproschema2redcap.py <input_dir_path> <output_csv_filename>"
        )
        sys.exit(1)
    input_dir_path = Path(sys.argv[1])
    output_csv_filename = sys.argv[2]
    main(input_dir_path, output_csv_filename)
