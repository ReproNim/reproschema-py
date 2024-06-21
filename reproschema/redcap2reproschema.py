import csv
import os
import re
from pathlib import Path

import yaml
from bs4 import BeautifulSoup

from .context_url import CONTEXTFILE_URL
from .models import Activity, Item, Protocol, write_obj_jsonld

matrix_group_count = {}

# All the mapping used in the code
SCHEMA_MAP = {
    "Variable / Field Name": "@id",  # column A
    # "Item Display Name": "prefLabel", # there is no column for this
    "Field Note": "description",
    # TODO: often "Field Annotation" has "@HIDDEN" and other markers
    # TODO: not sure if this can be every treated as description
    # "Field Annotation": "description",  # column R
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
    "datetime_": "xsd:dateTime",
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


def clean_header(header):
    cleaned_header = {}
    for k, v in header.items():
        # Strip BOM, whitespace, and enclosing quotation marks if present
        cleaned_key = k.lstrip("\ufeff").strip().strip('"')
        cleaned_header[cleaned_key] = v
    return cleaned_header


# TODO: normalized condition should depend on the field type, e.g., for SQL
def normalize_condition(condition_str, field_type=None):
    # Regular expressions for various pattern replacements
    # TODO: function doesn't remove <b></b> tags
    if isinstance(condition_str, bool):
        return condition_str
    elif isinstance(condition_str, str) and condition_str.lower() == "true":
        return True
    elif isinstance(condition_str, str) and condition_str.lower() == "false":
        return False
    elif condition_str is None:
        return None

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
        condition = normalize_condition(condition)
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
    if field_type not in INPUT_TYPE_MAP:
        raise Exception(
            f"Field type {field_type} is not currently supported, "
            f"supported types are {INPUT_TYPE_MAP.keys()}"
        )
    input_type = INPUT_TYPE_MAP.get(field_type)

    # Get the validation type from the field, if available
    validation_type = field.get(
        "Text Validation Type OR Show Slider Number", ""
    ).strip()

    if validation_type:
        # Map the validation type to an XSD type
        if validation_type not in VALUE_TYPE_MAP:
            raise Exception(
                f"Validation type {validation_type} is not currently supported, "
                f"supported types are {VALUE_TYPE_MAP.keys()}"
            )
        value_type = VALUE_TYPE_MAP.get(validation_type)
        # there are some specific input types in Reproschema that could be used instead of text
        if validation_type == "integer" and field_type == "text":
            input_type = "number"
        elif validation_type in ["float", "number"] and field_type == "text":
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
    else:  # set the default value type as string
        value_type = "xsd:string"
    return input_type, value_type


def process_choices(choices_str, field_name):
    if len(choices_str.split("|")) < 2:
        print(f"WARNING: I found only one option for choice: {choices_str}")

    choices = []
    choices_value_type = []
    for ii, choice in enumerate(choices_str.split("|")):
        parts = choice.split(", ")
        if len(parts) < 2:
            print(
                f"Warning: Invalid choice format '{choice}' in a {field_name} field, adding integer as a value"
            )
            # TODO! I'm adding int by default, but there is probably some legend in the csv and this is not yet implemented
            parts = [ii, parts[0]]
        # Try to convert the first part to an integer, if it fails, keep it as a string
        try:
            value = int(parts[0])
            choices_value_type.append("xsd:integer")
        except ValueError:
            value = parts[0]
            choices_value_type.append("xsd:string")
        choice_obj = {"name": {"en": " ".join(parts[1:])}, "value": value}
        # remove image for now
        # if len(parts) == 3:
        #     # Handle image url
        #     choice_obj["image"] = f"{parts[2]}.png"
        choices.append(choice_obj)
    return choices, list(set(choices_value_type))


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
    add_preable=True,
):
    """Process a row of the REDCap data and generate the jsonld file for the item."""
    global matrix_group_count
    matrix_group_name = field.get("Matrix Group Name", "")
    if matrix_group_name:
        matrix_group_count[matrix_group_name] = (
            matrix_group_count.get(matrix_group_name, 0) + 1
        )
        item_id = (
            f"{matrix_group_name}_{matrix_group_count[matrix_group_name]}"
        )
    else:
        item_id = field.get("Variable / Field Name", "")

    rowData = {
        "category": "reproschema:Item",
        "id": item_id,
        "prefLabel": {"en": item_id},  # there is no prefLabel in REDCap
        # "description": {"en": f"{item_id} of {form_name}"},
    }

    field_type = field.get("Field Type", "")
    input_type, value_type = parse_field_type_and_value(field)
    rowData["ui"] = {"inputType": input_type}
    rowData["responseOptions"] = {"valueType": [value_type]}

    # setting additional fields for some field types
    if field_type == "yesno":
        rowData["responseOptions"]["choices"] = [
            {"name": {"en": "Yes"}, "value": 1},
            {"name": {"en": "No"}, "value": 0},
        ]
    elif field_type == "checkbox":
        rowData["responseOptions"]["multipleChoice"] = True
    elif field_type in COMPUTE_LIST:
        rowData["ui"]["readonlyValue"] = True

    for key, value in field.items():
        if SCHEMA_MAP.get(key) in ["question", "description"] and value:
            rowData.update({SCHEMA_MAP[key]: parse_html(value)})
        elif SCHEMA_MAP.get(key) == "preamble" and value and add_preable:
            rowData.update({SCHEMA_MAP[key]: parse_html(value)})
        elif SCHEMA_MAP.get(key) == "allow" and value:
            rowData["ui"].update({"allow": value.split(", ")})
        # choices are only for some input_types
        elif (
            SCHEMA_MAP.get(key) == "choices"
            and value
            and input_type in ["radio", "select", "slider"]
        ):
            choices, choices_val_type_l = process_choices(
                value, field_name=field["Variable / Field Name"]
            )
            rowData["responseOptions"].update(
                {
                    "choices": choices,
                    "valueType": choices_val_type_l,
                },  # updating value type for choices (can be int or str)
            )
        # for now adding only for numerics, sometimes can be string or date.. TODO
        elif (
            SCHEMA_MAP.get(key) in RESPONSE_COND
            and value
            and value_type in ["xsd:integer", "xsd:decimal"]
        ):
            if value_type == "xsd:integer":
                try:
                    value = int(value)
                except ValueError:
                    print(f"Warning: Value {value} is not an integer")
                    continue
            elif value_type == "xsd:decimal":
                try:
                    value = float(value)
                except ValueError:
                    print(f"Warning: Value {value} is not a decimal")
                    continue
            rowData["responseOptions"].update({SCHEMA_MAP[key]: value})

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
    order,
    bl_list,
    matrix_list,  # TODO: in the future
    compute_list,
    preable=None,
):
    """Create the JSON-LD schema for the Activity."""
    # Use a set to track unique items and preserve order
    unique_order = list(dict.fromkeys(order))

    # Construct the JSON-LD structure
    json_ld = {
        "category": "reproschema:Activity",
        "id": f"{form_name}_schema",
        "prefLabel": {"en": activity_display_name},
        #        "description": {"en": activity_description},
        "schemaVersion": "1.0.0-rc4",
        "version": redcap_version,
        "ui": {
            "order": unique_order,
            "addProperties": bl_list,
            "shuffle": False,
        },
    }
    if preable:
        json_ld["preamble"] = parse_html(preable)
    if compute_list:
        json_ld["compute"] = compute_list

    act = Activity(**json_ld)
    # TODO (future):  remove or fix matrix info
    # remove matrixInfo to pass validation
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


def parse_language_iso_codes(input_string):
    soup = BeautifulSoup(input_string, "lxml")
    return [
        element.get("lang") for element in soup.find_all(True, {"lang": True})
    ]


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
                    f"{abs_folder_path}/activities/{form_name}/items",
                    exist_ok=True,
                )

            datas[form_name].append(row)

            # TODO: should we bring back the language
            # if not languages:
            #    languages = parse_language_iso_codes(row["Field Label"])

            field_name = row["Variable / Field Name"]
            if row.get("Field Type", "") in COMPUTE_LIST:
                # TODO: this right now doesn't give jsExpression
                condition = normalize_condition(
                    row["Choices, Calculations, OR Slider Labels"],
                    field_type=row["Field Type"],
                )
                compute[form_name].append(
                    {
                        "variableName": field_name,
                        "jsExpression": condition,
                    }
                )
            else:
                order[form_name].append(f"items/{field_name}")

    os.makedirs(f"{abs_folder_path}/{protocol_name}", exist_ok=True)
    return datas, order, compute, languages


# todo adding output path
def redcap2reproschema(
    csv_file, yaml_file, output_path, schema_context_url=None
):
    """
    Convert a REDCap data dictionary to Reproschema format.

    :param csv_file: Path to the REDCap CSV file.
    :param yaml_path: Path to the YAML configuration file.
    :param output_path: Path to the output dir, where protocol directory will be created
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

    protocol_name = protocol_name.replace(
        " ", "_"
    )  # Replacing spaces with underscores
    abs_folder_path = Path(output_path) / protocol_name
    abs_folder_path.mkdir(parents=True, exist_ok=True)

    if schema_context_url is None:
        schema_context_url = CONTEXTFILE_URL

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
        preambles_list = []

        for field in rows:
            # TODO (future): this probably can be done in proces_csv so don't have to run the loop again
            # TODO: Depends how the Matrix group should be treated
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
            preamble = field.get("Section Header", "").strip()
            if preamble:
                preambles_list.append(preamble)

        if len(set(preambles_list)) == 1:
            preamble_act = preambles_list[0]
            preamble_itm = False
        elif len(set(preambles_list)) == 0:
            preamble_act = None
            preamble_itm = False
        else:
            preamble_act = None
            preamble_itm = True

        activity_display_name = rows[0]["Form Name"]
        # todo: there is no form note in the csv
        activity_description = (
            ""  # rows[0].get("Form Note", "Default description")
        )

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
            preable=preamble_act,
        )

        # Process items after I know if preable belongs to the form or item
        for field in rows:
            field_name = field["Variable / Field Name"]
            print("Processing field: ", field_name, " in form: ", form_name)
            process_row(
                abs_folder_path,
                schema_context_url,
                form_name,
                field,
                add_preable=preamble_itm,
            )
        print("Processing activities", form_name)
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
