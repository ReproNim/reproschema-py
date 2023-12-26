import sys
import json
import csv
from pathlib import Path

def read_json_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return None

def find_Ftype_and_colH(item_json, row_data):
    """
    Find the field type and column header based on the given item_json.

    Args:
        item_json (dict): The JSON object containing the item information.
        row_data (dict): The row data dictionary.

    Returns:
        dict: The updated row data dictionary with field type and column header.

    """
    # Extract the input type from the item_json
    f_type = item_json.get('ui', {}).get('inputType', '')
    col_h = ''

    # Check the input type and update the field type and column header accordingly
    if f_type == 'integer':
        f_type = 'text'
        col_h = 'number'
    elif f_type == 'select':
        f_type = 'dropdown'
    elif f_type == 'date':
        f_type = 'text'
        col_h = 'ddate_mdy'

    # Update the row_data dictionary with the field type
    row_data['field_type'] = f_type

    # Update the row_data dictionary with the column header if available
    if col_h:
        row_data['val_type_OR_slider'] = col_h

    return row_data

def process_item(item_json, activity_name):
    """
    Process an item in JSON format and extract relevant information into a dictionary.

    Args:
        item_json (dict): The JSON object representing the item.
        activity_name (str): The name of the activity.

    Returns:
        dict: A dictionary containing the extracted information.
    """
    row_data = {}

    # Extract min and max values from response options, if available
    response_options = item_json.get('responseOptions', {})
    row_data['val_min'] = response_options.get('schema:minValue', '')
    row_data['val_max'] = response_options.get('schema:maxValue', '')

    choices = response_options.get('choices')
    if choices:
        if isinstance(choices, list):
            # Extract choice values and names, and join them with a '|'
            item_choices = [
                f"{ch.get('schema:value', ch.get('value', ''))}, {ch.get('schema:name', ch.get('name', ''))}"
                for ch in choices
            ]
            row_data['choices'] = ' | '.join(item_choices)
        elif isinstance(choices, str):
            row_data['choices'] = choices
        else:
            row_data['choices'] = ''

    row_data['required'] = response_options.get('requiredValue', '')

    row_data['field_notes'] = item_json.get('skos:altLabel', '')

    row_data['var_name'] = item_json.get('@id', '')
    row_data['activity'] = activity_name

    question = item_json.get('question')
    if isinstance(question, dict):
        row_data['field_label'] = question.get('en', '')
    elif isinstance(question, str):
        row_data['field_label'] = question
    else:
        row_data['field_label'] = ''

    # Call helper function to find Ftype and colH values and update row_data
    row_data = find_Ftype_and_colH(item_json, row_data)

    return row_data

def get_csv_data(dir_path):
    csv_data = []

    # Iterate over directories in dir_path
    for protocol_dir in dir_path.iterdir():
        if protocol_dir.is_dir():
            # Check for a _schema file in each directory
            schema_file = next(protocol_dir.glob('*_schema'), None)
            if schema_file:
                # Process the found _schema file
                parsed_protocol_json = read_json_file(schema_file)
                
                activity_order = parsed_protocol_json.get('ui', {}).get('order', [])
                for relative_activity_path in activity_order:
                    # Normalize the relative path and construct the absolute path
                    normalized_relative_path = Path(relative_activity_path.lstrip("../"))
                    activity_path = dir_path / normalized_relative_path
                    parsed_activity_json = read_json_file(activity_path)
                    
                    if parsed_activity_json:
                        item_order = parsed_activity_json.get('ui', {}).get('order', [])
                        for item in item_order:
                            item_path = activity_path.parent / item
                            item_json = read_json_file(item_path)
                            if item_json:
                                row_data = process_item(item_json, activity_path.stem)
                                csv_data.append(row_data)

                # Break after finding the first _schema file
                break
    
    return csv_data

def write_to_csv(csv_data, output_csv_filename):
    # Define the headers for the CSV file as per the JavaScript file
    headers = [
        'var_name', 'activity', 'section', 'field_type', 'field_label',
        'choices', 'field_notes', 'val_type_OR_slider', 'val_min', 'val_max',
        'identifier', 'visibility', 'required'
    ]

    # Writing to the CSV file
    with open(output_csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        for row in csv_data:
            writer.writerow(row)

    print('The CSV file was written successfully')

def main(input_dir_path, output_csv_filename):
    csv_data = get_csv_data(input_dir_path)
    write_to_csv(csv_data, output_csv_filename)

if __name__ == "__main__":
    # check if input_dir_path and output_csv_filename are provided
    if len(sys.argv) < 3:
        print("Usage: python reproschema2redcap.py <input_dir_path> <output_csv_filename>")
        sys.exit(1)
    input_dir_path = Path(sys.argv[1])
    output_csv_filename = sys.argv[2]
    main(input_dir_path, output_csv_filename)