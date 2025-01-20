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

def process_item(item, item_properties, activity_name, activity_preamble, contextfile, http_kwargs, compute_item=False, compute_expr=None):
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
            raise Exception(f"Expected to have ResponseOption but got {resp['category']}")
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
                item_choices = [f"{ch.value}, {ch.name.get('en', '')}" for ch in choices if ch.value is not None]
                if item_choices:
                    row_data["choices"] = " | ".join(item_choices)

    # Add valueRequired if explicitly True
    if item_properties and "valueRequired" in item_properties and item_properties["valueRequired"] is True:
        row_data["required"] = "y"
        
    var_name = str(item.id).split("/")[-1]  # Get the last part of the id path
    if var_name.endswith("_total_score"):
        row_data["isVis_logic"] = False  # This will make the field hidden
    # Regular isVis handling for other fields
    elif "isVis" in item_properties and item_properties["isVis"] is not True:
        row_data["isVis_logic"] = item_properties["isVis"]

    # Handle description
    if item.description and "en" in item.description and item.description["en"]:
        row_data["field_notes"] = item.description["en"]

    # Handle preamble
    if item.preamble and "en" in item.preamble and item.preamble["en"]:
        row_data["preamble"] = item.preamble["en"]
    elif activity_preamble:
        row_data["preamble"] = activity_preamble

    # Handle question/field label
    if compute_item:
        question = item.description
    else:
        question = item.question

    if isinstance(question, dict) and "en" in question and question["en"]:
        row_data["field_label"] = question["en"]
    elif isinstance(question, str) and question:
        row_data["field_label"] = question

    # Handle compute items
    if compute_item and compute_expr:
        print(f"\nDebug - Compute Item: {var_name}")
        print(f"Compute Expression: {compute_expr}")
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

                    # Get activity name without adding extra _schema
                    activity_name = act.id.split("/")[-1]
                    if activity_name.endswith('_schema.jsonld'):
                        activity_name = activity_name[:-12]  # Remove _schema.jsonld
                    elif activity_name.endswith('.jsonld'):
                        activity_name = activity_name[:-7]  # Remove .jsonld
                        
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

                        computed_fields = {calc_item.variableName for _, calc_item in item_calc}
    

                        for tp, item in item_order + item_calc:
                            try:
                                if tp == "calc":
                                    js_expr = item.jsExpression
                                    var_name = item.variableName
                    
                                    # Find the corresponding item properties
                                    if var_name in items_properties:
                                        item = items_properties[var_name]["isAbout"]
                                        # Ensure computed fields are marked as hidden
                                        items_properties[var_name]["isVis"] = False
                                    else:
                                        print(f"WARNING: no item properties found for computed field {var_name} in {activity_name}")
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
                                    item_json.pop("@context", "")
                                    itm = Item(**item_json)
                                except Exception as e:
                                    print(f"Error loading item: {item}")
                                    print(f"Error details: {str(e)}")
                                    continue
            
                                activity_name = act.id.split("/")[-1].split(".")[0]
                                activity_preamble = act.preamble.get("en", "").strip() if hasattr(act, 'preamble') else ""

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

                            except Exception as e:
                                print(f"Error processing item {item}: {str(e)}")
                                continue
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
        "Field Annotation"
    ]

    # Writing to the CSV file
    with open(output_csv_filename, "w", newline="", encoding="utf-8") as csvfile:
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
                "matrix_ranking": "Matrix Ranking?"
            }

            # Add mapped fields only if they exist and aren't empty
            for src_key, dest_key in field_mappings.items():
                if src_key in row and row[src_key] is not None and row[src_key] != "":
                    # Special handling for visibility logic
                    if src_key == "isVis_logic":
                        if row[src_key] is not True:  # Only add if not default True
                            redcap_row[dest_key] = row[src_key]
                    # Special handling for required field
                    elif src_key == "required":
                        redcap_row[dest_key] = "y" if row[src_key] else "n"
                    # Special handling for field annotation
                    elif src_key == "field_annotation":
                        current_annotation = redcap_row.get(dest_key, "")
                        if current_annotation:
                            redcap_row[dest_key] = f"{current_annotation} {row[src_key]}"
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
