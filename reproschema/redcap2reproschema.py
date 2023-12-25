# User inputs: these are specific to your protocol, fill out before using the script

# 1. your protocol id: use underscore for spaces, avoid special characters. 
#    The display name is the one that will show up in the app, this will be parsed as a string.
protocol_name = "sc_dd"

# 2. your protocol display name: this will show up in the app and be parsed as a string
protocol_display_name = "Your protocol display name"

# 3. create your raw GitHub repo URL
user_name = 'sanuann'
repo_name = 'reproschema'
branch_name = 'master'

your_repo_url = f"https://raw.githubusercontent.com/{user_name}/{repo_name}/{branch_name}"

# 4. add a description to your protocol
protocol_description = "Description for your protocol"

# 5. where are you hosting your images? For example: openmoji
image_path = 'https://raw.githubusercontent.com/hfg-gmuend/openmoji/master/color/618x618/'

import sys
import os
import csv
import json
import re
from collections import defaultdict
from bs4 import BeautifulSoup

def create_form_context_schema(form, row_list):
    item_obj = defaultdict(dict)
    item_obj["@version"] = 1.1
    item_obj[form] = f"{your_repo_url}/activities/{form}/items/"
    
    for field in row_list:
        field_name = field["Variable / Field Name"]
        item_obj[field_name] = {"@id": f"{form}:{field_name}", "@type": "@id"}

    form_context = {"@context": item_obj}
    fc = json.dumps(form_context, indent=4)

    try:
        with open(f"activities/{form}/{form}_context", "w") as file:
            file.write(fc)
        print(f"Context created for form {form}")
    except Exception as e:
        print(e)

def create_protocol_context(activity_list, your_repo_url, protocol_name):
    # Create protocol context file
    activity_obj = {
        "@version": 1.1,
        "activity_path": f"{your_repo_url}/activities/"
    }

    for activity in activity_list:
        # Define item_x urls to be inserted in context for the corresponding form
        activity_obj[activity] = {
            "@id": f"activity_path:{activity}/{activity}_schema",
            "@type": "@id"
        }

    protocol_context = {
        "@context": activity_obj
    }

    pc = json.dumps(protocol_context, indent=4)

    protocol_dir = f'protocols/{protocol_name}'
    os.makedirs(protocol_dir, exist_ok=True)

    with open(f'{protocol_dir}/{protocol_name}_context', 'w') as file:
        file.write(pc)

    print(f'Protocol context created for {protocol_name}')


def process_visibility(data):
    condition = data.get('Branching Logic (Show field only if...)')
    
    if condition:
        # Normalize the condition field to resemble a JavaScript-like condition
        condition = re.sub(r"\(([0-9]*)\)", r"___\1", condition)
        condition = re.sub(r"([^>|<])=", r"\1 ==", condition)
        condition = condition.replace(" and ", " && ")
        condition = condition.replace(" or ", " || ")
        condition = re.sub(r"\[([^\]]*)\]", r" \1 ", condition)

    visibility_obj = {
        "variableName": data['Variable / Field Name'],
        "isAbout": f"items/{data['Variable / Field Name']}",
        "isVis": condition if condition else True
    }
    return visibility_obj

def parse_field_type_and_value(data, input_type_map):
    field_type = data.get('Field Type', '')
    
    input_type = input_type_map.get(field_type, field_type)
    
    value_type_map = {
        'number': 'xsd:int',
        'date_': 'xsd:date',
        'datetime_': 'datetime',
        'time_': 'xsd:date',
        'email': 'email',
        'phone': 'phone'
    }
    validation_type = data.get('Text Validation Type OR Show Slider Number', '')
    
    value_type = value_type_map.get(validation_type, 'xsd:string')

    return input_type, value_type

def process_choices(choices_str, image_path):
    choices = []
    for choice in choices_str.split('|'):
        parts = choice.split(', ')
        choice_obj = {'schema:value': int(parts[0]), 'schema:name': parts[1]}
        if len(parts) == 3:
            choice_obj['schema:image'] = f"{image_path}{parts[2]}.png"
        choices.append(choice_obj)
    return choices

def normalize_condition(condition_str):
    condition_str = re.sub(r"\[([^\]]*)\]", r"\1", condition_str)
    condition_str = re.sub(r"\(([0-9]*)\)", r"___\1", condition_str)
    condition_str = condition_str.replace(" and ", " && ")
    condition_str = condition_str.replace(" or ", " || ")
    return condition_str

def write_to_file(form, field_name, rowData):
    try:
        file_path = os.path.join('activities', form, 'items', f'{field_name}')
        with open(file_path, 'w') as file:
            json.dump(rowData, file, indent=4)
        print(f"Item schema for {form} written successfully.")
    except Exception as e:
        print(f"Error in writing item schema for {form}: {e}")

def parse_html(input_string, default_language='en'):
    result = {}
    soup = BeautifulSoup(input_string, 'html.parser')

    lang_elements = soup.find_all(True, {'lang': True})
    if lang_elements:
        for element in lang_elements:
            lang = element.get('lang', default_language)
            text = element.get_text(strip=True)
            if text:
                result[lang] = text
        if not result:
            result[default_language] = soup.get_text(strip=True)
    else:
        result[default_language] = input_string

    return result

def process_row(schema_context_url, form, field, schema_map, input_type_map, ui_list, response_list, additional_notes_list):
    rowData = {
        '@context': schema_context_url,
        '@type': 'reproschema:Field',
    }

    field_type = field.get('Field Type', '')
    schema_map['Choices, Calculations, OR Slider Labels'] = 'scoringLogic' if field_type == 'calc' else 'choices'

    input_type, value_type = parse_field_type_and_value(field, input_type_map)
    rowData['ui'] = {'inputType': input_type}
    if value_type:
        rowData['responseOptions'] = {'valueType': value_type}

    for key, value in field.items():
        if schema_map.get(key) == 'allow' and value:
            rowData.setdefault('ui', {}).update({schema_map[key]: value.split(', ')})

        elif key in ui_list and value:
            rowData.setdefault('ui', {}).update({schema_map[key]: input_type_map.get(value, value)})

        elif key in response_list and value:
            if key == 'multipleChoice':
                value = value == '1'
            rowData.setdefault('responseOptions', {}).update({schema_map[key]: value})

        elif schema_map.get(key) == 'choices' and value:
            rowData.setdefault('responseOptions', {}).update({'choices': process_choices(value, image_path)})

        elif schema_map.get(key) == 'scoringLogic' and value:
            condition = normalize_condition(value)
            rowData.setdefault('ui', {}).update({'hidden': True})
            rowData.setdefault('scoringLogic', []).append({"variableName": field['Variable / Field Name'], "jsExpression": condition})

        elif schema_map.get(key) == 'visibility' and value:
            condition = normalize_condition(value)
            rowData.setdefault('visibility', []).append({"variableName": field['Variable / Field Name'], "isVis": condition})

        elif key in ['question', 'schema:description', 'preamble'] and value:
            rowData.update({schema_map[key]: parse_html(value)})

        elif key == 'Identifier?' and value:
            identifier_val = value.lower() == 'y'
            rowData.update({schema_map[key]: [{"legalStandard": "unknown", "isIdentifier": identifier_val}]})

        elif key in additional_notes_list and value:
            notes_obj = {"source": "redcap", "column": key, "value": value}
            rowData.setdefault('additionalNotesObj', []).append(notes_obj)

    write_to_file(form, field['Variable / Field Name'], rowData)

def create_form_schema(schema_context_url, form, activity_display_name, activity_description, order, bl_list, matrix_list, scores_list):
    # Construct the JSON-LD structure
    json_ld = {
        "@context": schema_context_url,
        "@type": "reproschema:Activity",
        "@id": f"{form}_schema",
        "prefLabel": activity_display_name,
        "description": activity_description,
        "schemaVersion": "1.0.0-rc4",
        "version": "0.0.1",
        "ui": {
            "order": order.get(form, []),
            "addProperties": bl_list,
            "shuffle": False
        }
    }

    if matrix_list:
        json_ld['matrixInfo'] = matrix_list
    if scores_list:
        json_ld['scoringLogic'] = scores_list

    try:
        path = f'activities/{form}'
        os.makedirs(path, exist_ok=True)  # Ensure the directory exists
        filename = f'{form}_schema'
        with open(os.path.join(path, filename), 'w') as file:
            json.dump(json_ld, file, indent=4)
        print(f"{form} Instrument schema created")
    except Exception as err:
        print(f"Error in writing {form} form schema:", err)

def process_activities(activity_name, protocol_visibility_obj, protocol_variable_map, protocol_order):
    # Set default visibility condition
    protocol_visibility_obj[activity_name] = True

    # Add activity to variableMap and Order
    protocol_variable_map.append({
        "variableName": activity_name,
        "isAbout": f"items/{activity_name}"
    })
    protocol_order.append(activity_name)

def create_protocol_schema(schema_context_url, protocol_name, protocol_display_name, protocol_description, protocol_variable_map, protocol_order, protocol_visibility_obj):
    # Construct the protocol schema
    protocol_schema = {
        "@context": schema_context_url,
        "@type": "reproschema:ActivitySet",
        "@id": f"{protocol_name}_schema",
        "skos:prefLabel": protocol_display_name,
        "skos:altLabel": f"{protocol_name}_schema",
        "schema:description": protocol_description,
        "schema:schemaVersion": "1.0.0-rc4",
        "schema:version": "0.0.1",
        "variableMap": protocol_variable_map,
        "ui": {
            "order": protocol_order,
            "shuffle": False,
            "visibility": protocol_visibility_obj
        }
    }

    # Write the protocol schema to a file
    try:
        os.makedirs(f'protocols/{protocol_name}', exist_ok=True)  # Ensure the directory exists
        with open(f'protocols/{protocol_name}/{protocol_name}_schema', 'w') as file:
            json.dump(protocol_schema, file, indent=4)
        print("Protocol schema created")
    except Exception as err:
        print("Error in writing protocol schema:", err)

def parse_language_iso_codes(input_string):
    soup = BeautifulSoup(input_string, 'lxml')
    return [element.get('lang') for element in soup.find_all(True, {'lang': True})]

def main(csv_path, schema_context_url):
    # Initialize variables
    schema_map = {
        "Variable / Field Name": "@id",
        "Item Display Name": "prefLabel",
        "Field Annotation": "description",
        "Section Header": "preamble",
        "Field Label": "question",
        "Field Type": "inputType",
        "Allow": "allow",
        "Required Field?": "requiredValue",
        "Text Validation Min": "minValue",
        "Text Validation Max": "maxValue",
        "Choices, Calculations, OR Slider Labels": "choices",
        "Branching Logic (Show field only if...)": "visibility",
        "Custom Alignment": "customAlignment",
        "Identifier?": "identifiable",
        "multipleChoice": "multipleChoice",
        "responseType": "@type"
    }

    input_type_map = {
        "calc": "number",
        "checkbox": "radio",
        "descriptive": "static",
        "dropdown": "select",
        "notes": "text"
    }

    ui_list = ['inputType', 'shuffle', 'allow', 'customAlignment']
    response_list = ['valueType', 'minValue', 'maxValue', 'requiredValue', 'multipleChoice']
    additional_notes_list = ['Field Note', 'Question Number (surveys only)']
    datas = {}
    order = {}
    bl_list = []
    sl_list = []
    visibility_obj = {}
    scores_obj = {}
    scores_list = []
    visibility_list = []
    languages = []
    variable_map = []
    matrix_list = []
    protocol_variable_map = []
    protocol_visibility_obj = {}
    protocol_order = []

    # Read and process the CSV file
    with open(csv_path, mode='r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            form_name = row['Form Name']
            datas.setdefault(form_name, []).append(row)
            os.makedirs(f'activities/{form_name}/items', exist_ok=True)
            os.makedirs(f'protocols/{protocol_name}', exist_ok=True)

            scores_list = []
            order[form_name] = []
            bl_list = []
            visibility_list = []
            variable_map = []
            matrix_list = []
            activity_display_name = row['Form Name']
            activity_description = row['Form Note']

            for field in datas[form_name]:
                if not languages:
                    languages = parse_language_iso_codes(field['Field Label'])

                field_name = field['Variable / Field Name']
                visibility_obj = process_visibility(field)
                bl_list.append(visibility_obj)
                variable_map.append({"variableName": field_name, "isAbout": f"items/{field_name}"})

                if field.get('Matrix Group Name') or field.get('Matrix Ranking?'):
                    matrix_list.append({"variableName": field_name, "matrixGroupName": field['Matrix Group Name'], "matrixRanking": field['Matrix Ranking?']})

                order[form_name].append(f"items/{field_name}")
                process_row(schema_context_url, form_name, field, schema_map, input_type_map, ui_list, response_list, additional_notes_list)

            create_form_schema(form_name, activity_display_name, activity_description, order[form_name], bl_list, matrix_list, scores_list)

        # Create protocol context and schema
        activity_list = list(datas.keys())
        for activity_name in activity_list:
            process_activities(activity_name, protocol_visibility_obj, protocol_variable_map, protocol_order)

        create_protocol_schema(schema_context_url, protocol_name, protocol_display_name, protocol_description, protocol_variable_map, protocol_order, protocol_visibility_obj)

if __name__ == "__main__":
    # Make sure we got a filename on the command line
    if len(sys.argv) < 3:
        print(f'Usage: {sys.argv[0]} your_data_dic.csv')
        sys.exit(1)

    # Read the CSV file
    csv_path = sys.argv[2]
    schema_context_url = 'https://raw.githubusercontent.com/ReproNim/reproschema/1.0.0-rc4/contexts/generic'

    main(csv_path, schema_context_url)
