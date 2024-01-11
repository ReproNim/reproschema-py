import os
import argparse
import csv
import json
import re
import yaml
from bs4 import BeautifulSoup


def normalize_condition(condition_str):
    re_parentheses = re.compile(r"\(([0-9]*)\)")
    re_non_gt_lt_equal = re.compile(r"([^>|<])=")
    re_brackets = re.compile(r"\[([^\]]*)\]")

    condition_str = re_parentheses.sub(r"___\1", condition_str)
    condition_str = re_non_gt_lt_equal.sub(r"\1 ==", condition_str)
    condition_str = condition_str.replace(" and ", " && ").replace(" or ", " || ")
    condition_str = re_brackets.sub(r" \1 ", condition_str)
    return condition_str


def process_visibility(data):
    condition = data.get("Branching Logic (Show field only if...)")
    if condition:
        condition = normalize_condition(condition)
    else:
        condition = True

    visibility_obj = {
        "variableName": data["Variable / Field Name"],
        "isAbout": f"items/{data['Variable / Field Name']}",
        "isVis": condition,
    }
    return visibility_obj

def parse_field_type_and_value(data, input_type_map):
    field_type = data.get("Field Type", "")

    input_type = input_type_map.get(field_type, field_type)

    value_type_map = {
        "number": "xsd:int",
        "date_": "xsd:date",
        "datetime_": "datetime",
        "time_": "xsd:date",
        "email": "email",
        "phone": "phone",
    }
    validation_type = data.get("Text Validation Type OR Show Slider Number", "")

    value_type = value_type_map.get(validation_type, "xsd:string")

    return input_type, value_type

def process_choices(field_type, choices_str):
    if field_type not in ['radio', 'dropdown']:  # Handle only radio and dropdown types
        return None

    choices = []
    for choice in choices_str.split("|"):
        parts = choice.split(", ")
        if len(parts) < 2:
            print(f"Warning: Skipping invalid choice format '{choice}' in a {field_type} field")
            continue

        # Try to convert the first part to an integer, if it fails, keep it as a string
        try:
            value = int(parts[0])
        except ValueError:
            value = parts[0]

        choice_obj = {"schema:value": value, "schema:name": parts[1]}
        if len(parts) == 3:
            # Handle image url
            choice_obj["schema:image"] = f"{parts[2]}.png"
        choices.append(choice_obj)
    return choices

def write_to_file(abs_folder_path, form_name, field_name, rowData):
    file_path = os.path.join(
        f"{abs_folder_path}", "activities", form_name, "items", f"{field_name}"
    )
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    try:
        with open(file_path, "w") as file:
            json.dump(rowData, file, indent=4)
        print(f"Item schema for {form_name} written successfully.")
    except Exception as e:
        print(f"Error in writing item schema for {form_name}: {e}")


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
        if not result:
            result[default_language] = soup.get_text(strip=True)
    else:
        result[default_language] = input_string

    return result


def process_row(
    abs_folder_path,
    schema_context_url,
    form_name,
    field,
    schema_map,
    input_type_map,
    ui_list,
    response_list,
    additional_notes_list,
):
    rowData = {
        "@context": schema_context_url,
        "@type": "reproschema:Field",
    }

    field_type = field.get("Field Type", "")
    schema_map["Choices, Calculations, OR Slider Labels"] = (
        "scoringLogic" if field_type == "calc" else "choices"
    )

    input_type, value_type = parse_field_type_and_value(field, input_type_map)
    rowData["ui"] = {"inputType": input_type}
    if value_type:
        rowData["responseOptions"] = {"valueType": value_type}

    if field_type == "yesno":
        rowData["responseOptions"] = {
            "valueType": "xsd:boolean",
            "choices": [
                {"schema:value": 1, "schema:name": "Yes"},
                {"schema:value": 0, "schema:name": "No"}
            ]
        }

    for key, value in field.items():
        if schema_map.get(key) == "allow" and value:
            rowData.setdefault("ui", {}).update({schema_map[key]: value.split(", ")})

        elif key in ui_list and value:
            rowData.setdefault("ui", {}).update(
                {schema_map[key]: input_type_map.get(value, value)}
            )

        elif key in response_list and value:
            if key == "multipleChoice":
                value = value == "1"
            rowData.setdefault("responseOptions", {}).update({schema_map[key]: value})

        elif schema_map.get(key) == "choices" and value:
            rowData.setdefault("responseOptions", {}).update(
                {"choices": process_choices(value)}
            )

        elif schema_map.get(key) == "scoringLogic" and value:
            condition = normalize_condition(value)
            rowData.setdefault("ui", {}).update({"hidden": True})
            rowData.setdefault("scoringLogic", []).append(
                {
                    "variableName": field["Variable / Field Name"],
                    "jsExpression": condition,
                }
            )

        elif schema_map.get(key) == "visibility" and value:
            condition = normalize_condition(value)
            rowData.setdefault("visibility", []).append(
                {"variableName": field["Variable / Field Name"], "isVis": condition}
            )

        elif key in ["question", "schema:description", "preamble"] and value:
            rowData.update({schema_map[key]: parse_html(value)})

        elif key == "Identifier?" and value:
            identifier_val = value.lower() == "y"
            rowData.update(
                {
                    schema_map[key]: [
                        {"legalStandard": "unknown", "isIdentifier": identifier_val}
                    ]
                }
            )

        elif key in additional_notes_list and value:
            notes_obj = {"source": "redcap", "column": key, "value": value}
            rowData.setdefault("additionalNotesObj", []).append(notes_obj)

    write_to_file(abs_folder_path, form_name, field["Variable / Field Name"], rowData)


def create_form_schema(
    abs_folder_path,
    schema_context_url,
    form_name,
    activity_display_name,
    activity_description,
    order,
    bl_list,
    matrix_list,
    scores_list,
):
    # Construct the JSON-LD structure
    json_ld = {
        "@context": schema_context_url,
        "@type": "reproschema:Activity",
        "@id": f"{form_name}_schema",
        "prefLabel": activity_display_name,
        "description": activity_description,
        "schemaVersion": "1.0.0-rc4",
        "version": "0.0.1",
        "ui": {
            "order": order.get(form_name, []),
            "addProperties": bl_list,
            "shuffle": False,
        },
    }

    if matrix_list:
        json_ld["matrixInfo"] = matrix_list
    if scores_list:
        json_ld["scoringLogic"] = scores_list

    path = os.path.join(f"{abs_folder_path}", "activities", form_name)
    filename = f"{form_name}_schema"
    file_path = os.path.join(path, filename)
    try:
        os.makedirs(path, exist_ok=True)
        with open(file_path, "w") as file:
            json.dump(json_ld, file, indent=4)
        print(f"{form_name} Instrument schema created")
    except OSError as e:
        print(f"Error creating directory {path}: {e}")
    except IOError as e:
        print(f"Error writing to file {file_path}: {e}")


def process_activities(activity_name, protocol_visibility_obj, protocol_order):
    # Set default visibility condition
    protocol_visibility_obj[activity_name] = True

    protocol_order.append(activity_name)


def create_protocol_schema(
    abs_folder_path,
    schema_context_url,
    protocol_name,
    protocol_display_name,
    protocol_description,
    protocol_order,
    protocol_visibility_obj,
):
    # Construct the protocol schema
    protocol_schema = {
        "@context": schema_context_url,
        "@type": "reproschema:Protocol",
        "@id": f"{protocol_name}_schema",
        "skos:prefLabel": protocol_display_name,
        "skos:altLabel": f"{protocol_name}_schema",
        "schema:description": protocol_description,
        "schema:schemaVersion": "1.0.0-rc4",
        "schema:version": "0.0.1",
        "ui": {
            "addProperties": [],
            "order": protocol_order,
            "shuffle": False,
        },
    }

    # Populate addProperties list
    for activity in protocol_order:
        add_property = {
            "isAbout": f"../activities/{activity}/{activity}_schema",
            "variableName": f"{activity}_schema",
            # Assuming activity name as prefLabel, update as needed
            "prefLabel": activity.replace("_", " ").title(),
        }
        protocol_schema["ui"]["addProperties"].append(add_property)

    # Add visibility if needed
    if protocol_visibility_obj:
        protocol_schema["ui"]["visibility"] = protocol_visibility_obj

    protocol_dir = f"{abs_folder_path}/{protocol_name}"
    schema_file = f"{protocol_name}_schema"
    file_path = os.path.join(protocol_dir, schema_file)

    try:
        os.makedirs(protocol_dir, exist_ok=True)
        with open(file_path, "w") as file:
            json.dump(protocol_schema, file, indent=4)
        print("Protocol schema created")
    except OSError as e:
        print(f"Error creating directory {protocol_dir}: {e}")
    except IOError as e:
        print(f"Error writing to file {file_path}: {e}")


def parse_language_iso_codes(input_string):
    soup = BeautifulSoup(input_string, "lxml")
    return [element.get("lang") for element in soup.find_all(True, {"lang": True})]


def process_csv(
    csv_file,
    abs_folder_path,
    schema_context_url,
    schema_map,
    input_type_map,
    ui_list,
    response_list,
    additional_notes_list,
    protocol_name,
):
    datas = {}
    order = {}
    languages = []

    with open(csv_file, mode="r", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            form_name = row["Form Name"]
            if form_name not in datas:
                datas[form_name] = []
                order[form_name] = []
                os.makedirs(
                    f"{abs_folder_path}/activities/{form_name}/items", exist_ok=True
                )

            datas[form_name].append(row)

            if not languages:
                languages = parse_language_iso_codes(row["Field Label"])

            for field in datas[form_name]:
                field_name = field["Variable / Field Name"]
                order[form_name].append(f"items/{field_name}")
                process_row(
                    abs_folder_path,
                    schema_context_url,
                    form_name,
                    field,
                    schema_map,
                    input_type_map,
                    ui_list,
                    response_list,
                    additional_notes_list,
                )

    os.makedirs(f"{abs_folder_path}/{protocol_name}", exist_ok=True)
    return datas, order, languages


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

    if not protocol_name:
        raise ValueError("Protocol name not specified in the YAML file.")

    protocol_name = protocol_name.replace(" ", "_")  # Replacing spaces with underscores

    # Check if the directory already exists
    if not os.path.exists(protocol_name):
        os.mkdir(protocol_name)  # Create the directory if it doesn't exist

    # Get absolute path of the local repository
    abs_folder_path = os.path.abspath(protocol_name)

    if schema_context_url is None:
        schema_context_url = "https://raw.githubusercontent.com/ReproNim/reproschema/1.0.0-rc4/contexts/generic"

    # Initialize variables
    schema_map = {
        "Variable / Field Name": "@id",  # column A
        "Item Display Name": "prefLabel",
        "Field Annotation": "description",  # column R
        "Section Header": "preamble",  # column C (need double-check)
        "Field Label": "question",  # column E
        "Field Type": "inputType",  # column D
        "Allow": "allow",
        "Required Field?": "requiredValue",  # column M
        "Text Validation Min": "minValue",  # column I
        "Text Validation Max": "maxValue",  # column J
        "Choices, Calculations, OR Slider Labels": "choices",  # column F
        "Branching Logic (Show field only if...)": "visibility",  # column L
        "Custom Alignment": "customAlignment",  # column N
        "Identifier?": "identifiable",  # column K
        "multipleChoice": "multipleChoice",
        "responseType": "@type",
    }

    input_type_map = {
        "calc": "number",
        "checkbox": "radio",
        "descriptive": "static",
        "dropdown": "select",
        "notes": "text",
    }

    ui_list = ["inputType", "shuffle", "allow", "customAlignment"]
    response_list = [
        "valueType",
        "minValue",
        "maxValue",
        "requiredValue",
        "multipleChoice",
    ]
    additional_notes_list = ["Field Note", "Question Number (surveys only)"]

    # Process the CSV file
    datas, order, _ = process_csv(
        csv_file,
        abs_folder_path,
        schema_context_url,
        schema_map,
        input_type_map,
        ui_list,
        response_list,
        additional_notes_list,
        protocol_name,
    )
    # Initialize other variables for protocol context and schema
    protocol_visibility_obj = {}
    protocol_order = []

    # Create form schemas and process activities
    for form_name, rows in datas.items():
        bl_list = []
        scores_list = []
        matrix_list = []

        for field in rows:
            visibility_obj = process_visibility(field)
            bl_list.append(visibility_obj)

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
            form_name,
            activity_display_name,
            activity_description,
            order,
            bl_list,
            matrix_list,
            scores_list,
        )

        process_activities(form_name, protocol_visibility_obj, protocol_order)

    # Create protocol schema
    create_protocol_schema(
        abs_folder_path,
        schema_context_url,
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

    # Call the main conversion function
    redcap2reproschema(args.csv_file, args.yaml_file)


if __name__ == "__main__":
    main()
