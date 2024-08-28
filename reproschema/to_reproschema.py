import os
from pathlib import Path
import yaml
from bs4 import BeautifulSoup
import re
import pandas as pd
import argparse

from .context_url import CONTEXTFILE_URL
from .jsonldutils import get_context_version
from .models import Activity, Item, Protocol, write_obj_jsonld

# Direct mapping from CSV columns to Reproschema fields
CSV_TO_REPROSCHEMA_MAP = {
    "activity_name": "Source From",
    "item_name": "Name",
    "inputType": "Field Type",
    "question": "Question",
    "response_option": "Option Values",
    "branch_logic": "REDCap Branching Logic",
    "description": "Description",
    "valueRequired": "REDCap Field Required",
    "validation": "REDCap Text Validation Type"
}

VALUE_TYPE_MAP = {
    "String": "xsd:string",
    "Enum": "xsd:enumeration",
    "Date": "xsd:date",
    "Time": "xsd:dateTime",
    "Numeric": "xsd:decimal",
    "Float": "xsd:decimal",
    "Integer": "xsd:integer",
    "Static": "xsd:string",
}

INPUT_TYPE_MAP = {
    "Numeric": "number",
    "Checkbox": "text",
    "Multi-select": "select",
    "Dropdown": "select",
    "Text": "text",
}

ADDITIONAL_NOTES_LIST = ["Domain", "Study", "Field Class", "Field Category", "Data Scope", "Source/Respondent", "Description Status"]

class CSVProcessor:
    def __init__(self, csv_file):
        self.csv_file = csv_file
        self.datas = {}
        self.order = {}

    def load_csv(self, abs_folder_path):
        df = pd.read_csv(self.csv_file)
        df.columns = df.columns.str.strip().str.replace('"', '')

        grouped = df.groupby(CSV_TO_REPROSCHEMA_MAP["activity_name"])
        for activity_name, group in grouped:
            activity_path = Path(abs_folder_path) / "activities" / activity_name / "items"
            activity_path.mkdir(parents=True, exist_ok=True)

            self.datas[activity_name] = group.to_dict(orient='records')
            self.order[activity_name] = [f"items/{item}" for item in group[CSV_TO_REPROSCHEMA_MAP["item_name"]]]

    def get_data(self):
        return self.datas, self.order

class ItemProcessor:
    def __init__(self):
        self.csv_to_reproschema_map = CSV_TO_REPROSCHEMA_MAP
        self.input_type_map = INPUT_TYPE_MAP
        self.value_type_map = VALUE_TYPE_MAP
        self.additional_notes_columns = ADDITIONAL_NOTES_LIST

    def branch_logic(self, condition_str):
        if not condition_str:
            return "true"
        
        condition_str = re.sub(r"\[([^\]]+)\]", r"\1", condition_str)
        condition_str = re.sub(r"([^><!=])=", r"\1===", condition_str)
        condition_str = re.sub(r"\bAND\b", " && ", condition_str, flags=re.IGNORECASE)
        condition_str = re.sub(r"\bOR\b", " || ", condition_str, flags=re.IGNORECASE)
        condition_str = re.sub(r"sum\(([^)]+)\)", r"[\1].reduce((a, b) => a + b, 0)", condition_str)
        return condition_str
    
    def process_item(self, item):
        input_type = self.input_type_map.get(item[self.csv_to_reproschema_map["inputType"]], "text")
        item_data = {
            "category": "reproschema:Item",
            "id": item[self.csv_to_reproschema_map["item_name"]],
            "prefLabel": {"en": item[self.csv_to_reproschema_map["item_name"]]},
            "question": {
                "en": self.clean_html(item[self.csv_to_reproschema_map["question"]])
            },
            "ui": {"inputType": input_type},
            "responseOptions": {
                "valueType": self.determine_value_type(item),
                "multipleChoice": item[self.csv_to_reproschema_map["inputType"]] == "Multi-select"
            }
        }

        if self.csv_to_reproschema_map["response_option"] in item:
            item_data["responseOptions"]["choices"], item_data["responseOptions"]["valueType"] = self.process_response_options(
                item[self.csv_to_reproschema_map["response_option"]],
                item_name=item[self.csv_to_reproschema_map["item_name"]]
            )

        for column in self.additional_notes_columns:
            if column in item and item[column]:  
                notes_obj = {"source": "redcap", "column": column, "value": item[column]}
                item_data.setdefault("additionalNotesObj", []).append(notes_obj)

        return item_data

    def determine_value_type(self, item):
        item_type = item[self.csv_to_reproschema_map["inputType"]]
        validation_type = item.get(self.csv_to_reproschema_map.get("validation", ""), "")
        
        # Ensure validation_type is a string before stripping
        if pd.isna(validation_type):
            validation_type = ""
        else:
            validation_type = str(validation_type).strip()

        return [self.value_type_map.get(validation_type, "xsd:string")]


    def process_response_options(self, response_option_str, item_name):
        if pd.isna(response_option_str):
            return [], ["xsd:string"]  # Return an empty list and default value type if response options are missing

        response_option = []
        response_option_value_type = []

        # Ensure that response_option_str is treated as a string
        response_option_str = str(response_option_str)

        # Process the second format: "NULL=>''{-}'0'=>'Not bothered at all'{-}'1'=>'Bothered a little'{-}'2'=>'Bothered a lot'"
        choice_pairs = response_option_str.split("{-}")
        for choice in choice_pairs:
            key_value = choice.split("=>")
            if len(key_value) == 2:
                value = key_value[0].strip().strip("'")
                
                # Skip if the value is "NULL"
                if value == "NULL":
                    continue
                
                name = self.clean_html(key_value[1].strip().strip("'"))

                # Try to convert the value to an integer, if possible
                try:
                    value = int(value)
                    response_option_value_type.append("xsd:integer")
                except ValueError:
                    # If it's not an integer, treat it as a string
                    response_option_value_type.append("xsd:string")

                response_option.append({"name": {"en": name}, "value": value})
            else:
                print(f"Warning: Invalid choice format '{choice}' in {item_name} field")

        return response_option, list(set(response_option_value_type))


    def clean_html(self, raw_html):
        """Helper function to clean up HTML tags and return plain text"""
        if pd.isna(raw_html):
            return ""  # Return an empty string if the value is NaN

        soup = BeautifulSoup(str(raw_html), "html.parser")
        return soup.get_text()


class ActivitySchema:
    def __init__(self, activity_name, activity_display_name, redcap_version):
        self.activity_name = activity_name
        self.activity_display_name = activity_display_name
        self.redcap_version = redcap_version
        self.items = []

    def add_item(self, item_data):
        self.items.append(item_data)

    def create_activity_schema(self, abs_folder_path, order, bl_list):
        json_ld = {
            "category": "reproschema:Activity",
            "id": f"{self.activity_name}_schema",
            "prefLabel": {"en": self.activity_display_name},
            "schemaVersion": get_context_version(CONTEXTFILE_URL),
            "version": self.redcap_version,
            "ui": {
                "order": list(dict.fromkeys(order)),
                "addProperties": bl_list,
                "shuffle": False,
            },
        }

        act = Activity(**json_ld)
        path = Path(abs_folder_path) / "activities" / self.activity_name
        path.mkdir(parents=True, exist_ok=True)
        file_path = path / f"{self.activity_name}_schema"
        write_obj_jsonld(act, file_path, contextfile_url=CONTEXTFILE_URL)
        print(f"{self.activity_name} Instrument schema created")

class ProtocolSchema:
    def __init__(self, protocol_name, protocol_display_name, redcap_version, protocol_description=""):
        self.protocol_name = protocol_name
        self.protocol_display_name = protocol_display_name
        self.redcap_version = redcap_version
        self.protocol_description = protocol_description
        self.activities = []

    def add_activity(self, activity_name, protocol_visibility_obj):
        protocol_visibility_obj[activity_name] = True
        self.activities.append(activity_name)

    def create_protocol_schema(self, abs_folder_path, protocol_order, protocol_visibility_obj):
        protocol_schema = {
            "category": "reproschema:Protocol",
            "id": f"{self.protocol_name}_schema",
            "prefLabel": {"en": self.protocol_display_name},
            "description": {"en": self.protocol_description},
            "schemaVersion": get_context_version(CONTEXTFILE_URL),
            "version": self.redcap_version,
            "ui": {
                "addProperties": [],
                "order": [],
                "shuffle": False,
            },
        }

        for activity in protocol_order:
            full_path = f"../activities/{activity}/{activity}_schema"
            add_property = {
                "isAbout": full_path,
                "variableName": f"{activity}_schema",
                "prefLabel": {"en": activity.replace("_", " ").title()},
                "isVis": protocol_visibility_obj.get(activity, True),
            }
            protocol_schema["ui"]["addProperties"].append(add_property)
            protocol_schema["ui"]["order"].append(full_path)

        prot = Protocol(**protocol_schema)
        protocol_dir = Path(abs_folder_path) / self.protocol_name
        protocol_dir.mkdir(parents=True, exist_ok=True)
        schema_file = f"{self.protocol_name}_schema"
        file_path = protocol_dir / schema_file
        write_obj_jsonld(prot, file_path, contextfile_url=CONTEXTFILE_URL)
        print(f"Protocol schema created in {file_path}")

def to_reproschema(csv_file, yaml_file, output_path):
    csv_processor = CSVProcessor(csv_file=csv_file)
    item_processor = ItemProcessor()

    with open(yaml_file, "r") as f:
        protocol = yaml.safe_load(f)

    protocol_name = protocol.get("protocol_name").replace(" ", "_")
    abs_folder_path = Path(output_path) / protocol_name
    abs_folder_path.mkdir(parents=True, exist_ok=True)

    csv_processor.load_csv(abs_folder_path)
    datas, order = csv_processor.get_data()

    protocol_visibility_obj = {}
    protocol_order = []

    for activity_name, rows in datas.items():
        activity_schema = ActivitySchema(
            activity_name,
            rows[0][CSV_TO_REPROSCHEMA_MAP["activity_name"]],
            protocol["redcap_version"]
        )

        bl_list = []

        for idx, item in enumerate(rows):  
            item_data = item_processor.process_item(item)

            # Handle "description" as a dictionary
            item_data["description"] = {"en": f"Q[{idx}] of {activity_name}"}

            item_name = item[CSV_TO_REPROSCHEMA_MAP["item_name"]]
            it = Item(**item_data)
            file_path_item = Path(abs_folder_path) / "activities" / activity_name / "items" / item_name
            write_obj_jsonld(it, file_path_item, contextfile_url=CONTEXTFILE_URL)

            activity_schema.add_item(item_data)

            # Handle "valueRequired" for bl_list separately
            if not pd.isna(item[CSV_TO_REPROSCHEMA_MAP["valueRequired"]]):
                value_required = str(item[CSV_TO_REPROSCHEMA_MAP["valueRequired"]]) == '1'
            else:
                value_required = False

            # Add to bl_list
            annotation = item.get(CSV_TO_REPROSCHEMA_MAP.get("annotation", ""), "")
            is_vis = "@HIDDEN" not in annotation
            bl_list.append({
                "variableName": item_name,
                "isAbout": f"items/{item_name}",
                "valueRequired": value_required,
                "isVis": is_vis,  
            })

        activity_schema.create_activity_schema(
            abs_folder_path,
            order[activity_name],
            bl_list,
        )

        protocol_order.append(activity_name)

    protocol_schema = ProtocolSchema(
        protocol_name,
        protocol.get("protocol_display_name"),
        protocol.get("redcap_version"),
        protocol.get("protocol_description", "")
    )
    protocol_schema.create_protocol_schema(
        abs_folder_path,
        protocol_order,
        protocol_visibility_obj
    )

def main():
    parser = argparse.ArgumentParser(description="Convert a CSV file to Reproschema format.")
    parser.add_argument("csv_file", help="Path to the input CSV file.")
    parser.add_argument("yaml_file", help="Path to the YAML configuration file.")
    parser.add_argument("output_path", help="Path to the directory where the output schemas will be saved.")

    args = parser.parse_args()

    to_reproschema(
        csv_file=args.csv_file,
        yaml_file=args.yaml_file,
        output_path=args.output_path,
    )

if __name__ == "__main__":
    main()