import os
import argparse
import csv
import json
import re
import yaml
from bs4 import BeautifulSoup
from .models import Activity, Item, Protocol, write_obj_jsonld
from .utils import CONTEXTFILE_URL

matrix_group_count = {}

# All the mapping used in the code
SCHEMA_MAP = {
    "Variable / Field Name": "@id",  # column A
    "Item Display Name": "prefLabel",
    "Field Annotation": "description",  # column R
    "Section Header": "preamble",  # column C (need double-check)
    "Field Label": "question",  # column E
    "Field Type": "inputType",  # column D
    "Allow": "allow",
    "Required Field?": "valueRequired",  # column M
    "Text Validation Min": "minValue",  # column I
    "Text Validation Max": "maxValue",  # column J
    "Choices, Calculations, OR Slider Labels": "choices",  # column F
    "Branching Logic (Show field only if...)": "visibility",  # column L
    "Custom Alignment": "customAlignment",  # column N
    # "Identifier?": "identifiable",  # column K # todo: should we remove the identifiers completely?
    "multipleChoice": "multipleChoice",
    "responseType": "@type",
}

INPUT_TYPE_MAP = {
    "calc": "number",
    "checkbox": "radio",
    "descriptive": "static",
    "dropdown": "select",
    "notes": "text",
}

UI_LIST = ["inputType", "shuffle", "allow", "customAlignment"]
RESPONSE_LIST = [
    "valueType",
    # TODO: minValue and maxValue can be strings???
    # "minValue",
    # "maxValue",
    "multipleChoice",
]
ADDITIONAL_NOTES_LIST = ["Field Note", "Question Number (surveys only)"]


def clean_header(header):
    cleaned_header = {}
    for k, v in header.items():
        # Strip BOM, whitespace, and enclosing quotation marks if present
        cleaned_key = k.lstrip("\ufeff").strip().strip('"')
        cleaned_header[cleaned_key] = v
    return cleaned_header


def normalize_condition(condition_str):
    # Regular expressions for various pattern replacements
    re_parentheses = re.compile(r"\(([0-9]*)\)")
    re_non_gt_lt_equal = re.compile(r"([^>|<])=")
    re_brackets = re.compile(r"\[([^\]]*)\]")
    re_extra_spaces = re.compile(r"\s+")
    re_double_quotes = re.compile(r'"')
    re_or = re.compile(r"\bor\b")  # Match 'or' as whole word

    # Apply regex replacements
    condition_str = re_parentheses.sub(r"___\1", condition_str)
    condition_str = re_non_gt_lt_equal.sub(r"\1 ==", condition_str)
    condition_str = re_brackets.sub(r" \1 ", condition_str)

    # Replace 'or' with '||', ensuring not to replace '||'
    condition_str = re_or.sub("||", condition_str)

    # Replace 'and' with '&&'
    condition_str = condition_str.replace(" and ", " && ")

    # Trim extra spaces and replace double quotes with single quotes
    condition_str = re_extra_spaces.sub(
        " ", condition_str
    ).strip()  # Reduce multiple spaces to a single space
    condition_str = re_double_quotes.sub(
        "'", condition_str
    )  # Replace double quotes with single quotes

    return condition_str.strip()


def process_field_properties(data):
    """Getting information about the item that will be used in the Activity schema"""
    condition = data.get("Branching Logic (Show field only if...)")
    if condition:
        # TODO: there are situations when both condition is set and Field Type is calc, what should be used in isVis?
        # if data["Field Type"] == "calc": breakpoint()
        condition = normalize_condition(condition)
    elif data["Field Type"] == "calc":
        condition = False
    else:
        condition = True

    prop_obj = {
        "variableName": data["Variable / Field Name"],
        "isAbout": f"items/{data['Variable / Field Name']}",
        "isVis": condition,
    }
    if data["Required Field?"]:
        if data["Required Field?"] in "y":
            prop_obj["valueRequired"] = True
        else:
            raise (
                f"value {data['Required Field?']} not supported yet for redcap:Required Field?"
            )
    return prop_obj


def parse_field_type_and_value(field):
    field_type = field.get("Field Type", "")
    # Check if field_type is 'yesno' and directly assign 'radio' as the input type
    if field_type == "yesno":
        input_type = "radio"  # Directly set to 'radio' for 'yesno' fields
    else:
        input_type = INPUT_TYPE_MAP.get(field_type, field_type)  # Original logic

    # Initialize the default value type as string
    value_type = "xsd:string"

    # Map certain field types directly to xsd types
    value_type_map = {
        "text": "xsd:string",
        "date_": "xsd:date",
        "datetime_": "xsd:dateTime",
        "time_": "xsd:time",
        "email": "xsd:string",
        "phone": "xsd:string",
        # No change needed here for 'yesno', as it's handled above
    }

    # Get the validation type from the field, if available
    validation_type = field.get(
        "Text Validation Type OR Show Slider Number", ""
    ).strip()

    if validation_type:
        # Map the validation type to an XSD type if it's in the map
        value_type = value_type_map.get(validation_type, "xsd:string")
    elif field_type in ["radio", "dropdown"]:
        # If there's no validation type, but the field type is radio or dropdown, use xsd:integer
        value_type = "xsd:integer"

    return input_type, value_type


def process_choices(field_type, choices_str):
    if field_type not in ["radio", "dropdown"]:  # Handle only radio and dropdown types
        return None

    choices = []
    for choice in choices_str.split("|"):
        parts = choice.split(", ")
        if len(parts) < 2:
            print(
                f"Warning: Skipping invalid choice format '{choice}' in a {field_type} field"
            )
            continue

        # Try to convert the first part to an integer, if it fails, keep it as a string
        try:
            value = int(parts[0])
        except ValueError:
            value = parts[0]

        choice_obj = {"name": {"en": " ".join(parts[1:])}, "value": value}
        # remove image for now
        # if len(parts) == 3:
        #     # Handle image url
        #     choice_obj["image"] = f"{parts[2]}.png"
        choices.append(choice_obj)
    return choices


def parse_html(input_string, default_language="en"):
    result = {}
    soup = BeautifulSoup(input_string, "html.parser")

    lang_elements = soup.find_all(True, {"lang": True})
    if lang_elements:
        for element in lang_elements:
            lang = element.get("lang", default_language)
            text = element.get_text(strip=True)
            if text:
                result[lang] = text
        if not result:  # If no text was extracted
            result[default_language] = soup.get_text(strip=True)
    else:
        result[default_language] = soup.get_text(
            strip=True
        )  # Use the entire text as default language text

    return result


def process_row(
    abs_folder_path,
    schema_context_url,
    form_name,
    field,
):
    """Process a row of the REDCap data and generate the jsonld file for the item."""
    global matrix_group_count
    matrix_group_name = field.get("Matrix Group Name", "")
    if matrix_group_name:
        matrix_group_count[matrix_group_name] = (
            matrix_group_count.get(matrix_group_name, 0) + 1
        )
        item_id = f"{matrix_group_name}_{matrix_group_count[matrix_group_name]}"
    else:
        item_id = field.get("Variable / Field Name", "")

    rowData = {
        "category": "reproschema:Item",
        "id": item_id,
        "prefLabel": {"en": item_id},
        "description": {"en": f"{item_id} of {form_name}"},
    }

    field_type = field.get("Field Type", "")
    input_type, value_type = parse_field_type_and_value(field)
    rowData["ui"] = {"inputType": input_type}
    if value_type:
        rowData["responseOptions"] = {"valueType": value_type}

    if field_type == "yesno":
        rowData["responseOptions"] = {
            "valueType": "xsd:boolean",
            "choices": [
                {"name": {"en": "Yes"}, "value": 1},
                {"name": {"en": "No"}, "value": 0},
            ],
        }

    for key, value in field.items():
        if SCHEMA_MAP.get(key) in ["question", "description", "preamble"] and value:
            rowData.update({SCHEMA_MAP[key]: parse_html(value)})

        elif SCHEMA_MAP.get(key) == "allow" and value:
            rowData.setdefault("ui", {}).update({SCHEMA_MAP[key]: value.split(", ")})

        elif key in UI_LIST and value:  # this is wrong
            rowData.setdefault("ui", {}).update(
                {SCHEMA_MAP[key]: INPUT_TYPE_MAP.get(value, value)}
            )

        elif SCHEMA_MAP.get(key) in RESPONSE_LIST and value:
            if key == "multipleChoice":
                value = value == "1"
            rowData.setdefault("responseOptions", {}).update({SCHEMA_MAP[key]: value})

        elif SCHEMA_MAP.get(key) == "choices" and value:
            # in case it's not choices but calc (used in score computing)
            if field_type != "calc":
                # Pass both field_type and value to process_choices
                rowData.setdefault("responseOptions", {}).update(
                    {"choices": process_choices(field_type, value)}
                )

        # elif key == "Identifier?" and value:
        #     identifier_val = value.lower() == "y"
        #     rowData.update(
        #         {
        #             schema_map[key]: [
        #                 {"legalStandard": "unknown", "isIdentifier": identifier_val}
        #             ]
        #         }
        #     )

        elif key in ADDITIONAL_NOTES_LIST and value:
            notes_obj = {"source": "redcap", "column": key, "value": value}
            rowData.setdefault("additionalNotesObj", []).append(notes_obj)

    it = Item(**rowData)
    file_path_item = os.path.join(
        f"{abs_folder_path}",
        "activities",
        form_name,
        "items",
        f'{field["Variable / Field Name"]}',
    )

    write_obj_jsonld(it, file_path_item, contextfile_url=schema_context_url)


# create activity
def create_form_schema(
    abs_folder_path,
    schema_context_url,
    redcap_version,
    form_name,
    activity_display_name,
    activity_description,
    order,  # todo
    bl_list,
    matrix_list,  # TODO:
    compute_list,
):
    """Create the JSON-LD schema for the Activity."""
    # Use a set to track unique items and preserve order
    unique_order = list(dict.fromkeys(order))

    # Construct the JSON-LD structure
    json_ld = {
        "category": "reproschema:Activity",
        "id": f"{form_name}_schema",
        "prefLabel": {"en": activity_display_name},
        "description": {"en": activity_description},
        "schemaVersion": "1.0.0-rc4",
        "version": redcap_version,
        "ui": {
            "order": unique_order,
            "addProperties": bl_list,
            "shuffle": False,
        },
    }

    if compute_list:
        json_ld["compute"] = compute_list

    act = Activity(**json_ld)
    # TODO: should we completely remove matrixInfo??
    # remove matrixInfo to pass validataion
    # if matrix_list:
    #     json_ld["matrixInfo"] = matrix_list

    path = os.path.join(f"{abs_folder_path}", "activities", form_name)
    os.makedirs(path, exist_ok=True)
    filename = f"{form_name}_schema"
    file_path = os.path.join(path, filename)
    write_obj_jsonld(act, file_path, contextfile_url=schema_context_url)
    print(f"{form_name} Instrument schema created")


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
        "altLabel": {"en": f"{protocol_name}_schema"},
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


def parse_language_iso_codes(input_string):
    soup = BeautifulSoup(input_string, "lxml")
    return [element.get("lang") for element in soup.find_all(True, {"lang": True})]


def process_csv(
    csv_file,
    abs_folder_path,
    schema_context_url,
    protocol_name,
):
    datas = {}
    order = {}
    compute = {}
    languages = []

    with open(csv_file, mode="r", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            row = clean_header(row)
            form_name = row["Form Name"]
            if form_name not in datas:
                datas[form_name] = []
                order[form_name] = []
                compute[form_name] = []
                os.makedirs(
                    f"{abs_folder_path}/activities/{form_name}/items", exist_ok=True
                )

            datas[form_name].append(row)

            if not languages:
                languages = parse_language_iso_codes(row["Field Label"])

            for field in datas[form_name]:
                if field.get("Field Type", "") == "calc":
                    condition = normalize_condition(
                        field["Choices, Calculations, OR Slider Labels"]
                    )
                    compute[form_name].append(
                        {
                            "variableName": field["Variable / Field Name"],
                            "jsExpression": condition,
                        }
                    )
                field_name = field["Variable / Field Name"]
                order[form_name].append(f"items/{field_name}")
                print("Processing field: ", field_name, " in form: ", form_name)
                process_row(
                    abs_folder_path,
                    schema_context_url,
                    form_name,
                    field,
                )

    os.makedirs(f"{abs_folder_path}/{protocol_name}", exist_ok=True)
    return datas, order, compute, languages


# todo adding output path
def redcap2reproschema(csv_file, yaml_file, schema_context_url=None):
    """
    Convert a REDCap data dictionary to Reproschema format.

    :param csv_file: Path to the REDCap CSV file.
    :param yaml_path: Path to the YAML configuration file.
    :param schema_context_url: URL of the schema context. Optional.
    """

    # Read the YAML configuration
    with open(yaml_file, "r") as f:
        protocol = yaml.safe_load(f)

    protocol_name = protocol.get("protocol_name")
    protocol_display_name = protocol.get("protocol_display_name")
    protocol_description = protocol.get("protocol_description")
    redcap_version = protocol.get("redcap_version")
    # we can add reproschema version here (or automatically extract)

    if not protocol_name:
        raise ValueError("Protocol name not specified in the YAML file.")

    protocol_name = protocol_name.replace(" ", "_")  # Replacing spaces with underscores

    # Check if the directory already exists
    if not os.path.exists(protocol_name):
        os.mkdir(protocol_name)  # Create the directory if it doesn't exist

    # Get absolute path of the local repository
    abs_folder_path = os.path.abspath(protocol_name)

    if schema_context_url is None:
        schema_context_url = CONTEXTFILE_URL

    # Initialize variables

    # Process the CSV file
    datas, order, compute, _ = process_csv(
        csv_file,
        abs_folder_path,
        schema_context_url,
        protocol_name,
    )
    # Initialize other variables for protocol context and schema
    protocol_visibility_obj = {}
    protocol_order = []

    # Create form schemas and process activities
    for form_name, rows in datas.items():
        bl_list = []
        matrix_list = []

        for field in rows:
            # TODO (future): this probably can be done in proces_csv so don't have to run the loop again
            field_properties = process_field_properties(field)
            bl_list.append(field_properties)
            if field.get("Matrix Group Name") or field.get("Matrix Ranking?"):
                matrix_list.append(
                    {
                        "variableName": field["Variable / Field Name"],
                        "matrixGroupName": field["Matrix Group Name"],
                        "matrixRanking": field["Matrix Ranking?"],
                    }
                )

        activity_display_name = rows[0]["Form Name"]
        activity_description = rows[0].get("Form Note", "Default description")

        create_form_schema(
            abs_folder_path,
            schema_context_url,
            redcap_version,
            form_name,
            activity_display_name,
            activity_description,
            order[form_name],
            bl_list,
            matrix_list,
            compute[form_name],
        )

        process_activities(form_name, protocol_visibility_obj, protocol_order)

    # Create protocol schema
    create_protocol_schema(
        abs_folder_path,
        schema_context_url,
        redcap_version,
        protocol_name,
        protocol_display_name,
        protocol_description,
        protocol_order,
        protocol_visibility_obj,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Convert REDCap data dictionary to Reproschema format."
    )
    parser.add_argument("csv_file", help="Path to the REDCap data dictionary CSV file.")
    parser.add_argument("yaml_file", help="Path to the Reproschema protocol YAML file.")
    args = parser.parse_args()

    redcap2reproschema(args.csv_file, args.yaml_file)


if __name__ == "__main__":
    main()
