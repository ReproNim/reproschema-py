import argparse
import re
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import yaml
from bs4 import BeautifulSoup

from .context_url import CONTEXTFILE_URL
from .jsonldutils import get_context_version
from .mappings import (
    ADDITIONAL_NOTES_LIST,
    CSV_TO_REPROSCHEMA_MAP,
    INPUT_TYPE_MAP,
    VALUE_TYPE_MAP,
)
from .models import Activity, Item, Protocol, write_obj_jsonld


def load_config(config_file: str) -> Dict[str, Any]:
    with open(config_file, "r") as f:
        return yaml.safe_load(f)


class ReproSchemaConverter:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.csv_to_reproschema_map = CSV_TO_REPROSCHEMA_MAP
        self.value_type_map = VALUE_TYPE_MAP
        self.input_type_map = INPUT_TYPE_MAP
        self.additional_notes_columns = ADDITIONAL_NOTES_LIST
        self.branch_logic_pattern = re.compile(
            r"\[([^\]]+)\]|\b(AND|OR)\b|([^><!=])=|sum\(([^)]+)\)"
        )

    def load_csv(self, csv_file: str) -> pd.DataFrame:
        df = pd.read_csv(csv_file)
        df.columns = df.columns.str.strip().str.replace('"', "")
        return df

    def process_dataframe(self, df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        grouped = df.groupby(self.csv_to_reproschema_map["activity_name"])
        activities = {}
        for activity_name, group in grouped:
            items = [
                self.process_item(item) for item in group.to_dict("records")
            ]
            activities[activity_name] = {
                "items": items,
                "order": [f"items/{item['id']}" for item in items],
                "compute": self.generate_compute_section(items),
            }
        return activities

    def process_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        input_type = self.input_type_map.get(
            item[self.csv_to_reproschema_map["inputType"]], "text"
        )
        item_data = {
            "category": "reproschema:Item",
            "id": item[self.csv_to_reproschema_map["item_name"]],
            "prefLabel": {
                "en": item[self.csv_to_reproschema_map["item_name"]]
            },
            "question": {
                "en": self.clean_html(
                    item[self.csv_to_reproschema_map["question"]]
                )
            },
            "ui": {"inputType": input_type},
            "responseOptions": {
                "valueType": self.determine_value_type(item),
                "multipleChoice": item[
                    self.csv_to_reproschema_map["inputType"]
                ]
                == "Multi-select",
            },
        }

        if self.csv_to_reproschema_map["response_option"] in item:
            (
                item_data["responseOptions"]["choices"],
                item_data["responseOptions"]["valueType"],
            ) = self.process_response_options(
                item[self.csv_to_reproschema_map["response_option"]],
                item[self.csv_to_reproschema_map["item_name"]],
            )

        item_data["additionalNotesObj"] = self.process_additional_notes(item)

        return item_data

    def determine_value_type(self, item: Dict[str, Any]) -> List[str]:
        validation_type = item.get(
            self.csv_to_reproschema_map.get("validation", ""), ""
        )

        # Ensure validation_type is a string before stripping
        if pd.isna(validation_type):
            validation_type = ""
        else:
            validation_type = str(validation_type).strip()

        return [self.value_type_map.get(validation_type, "xsd:string")]

    def process_response_options(
        self, response_option_str: str, item_name: str
    ) -> tuple:
        if pd.isna(response_option_str):
            return [], ["xsd:string"]

        response_option = []
        response_option_value_type = set()

        choices = response_option_str.split("{-}")
        for choice in choices:
            match = re.match(r"'([^']+)'=>'([^']+)'", choice.strip())
            if match:
                value, name = match.groups()
                response_option.append({"name": {"en": name}, "value": value})
                response_option_value_type.add("xsd:string")
            else:
                print(
                    f"Warning: Invalid choice format '{choice}' in {item_name} field"
                )

        return response_option, list(response_option_value_type)

    def process_additional_notes(
        self, item: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        return [
            {"source": "redcap", "column": column, "value": item[column]}
            for column in self.additional_notes_columns
            if column in item and item[column]
        ]

    def clean_html(self, raw_html: str) -> str:
        if pd.isna(raw_html):
            return ""
        if "<" in str(raw_html) and ">" in str(raw_html):
            return BeautifulSoup(str(raw_html), "html.parser").get_text()
        return str(raw_html)

    def generate_compute_section(
        self, items: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        compute_items = []
        for item in items:
            if "_Score" in item["id"] or "_score" in item["id"]:
                compute_items.append(
                    {"variableName": item["id"], "jsExpression": ""}
                )
        return compute_items

    def branch_logic(self, condition_str):
        if not condition_str:
            return "true"

        def replace_func(match):
            if match.group(1):  # [variable] -> variable
                return match.group(1)
            elif match.group(2):  # AND|OR -> && or ||
                return " && " if match.group(2).lower() == "and" else " || "
            elif match.group(3):  # single = -> ===
                return match.group(3) + "==="
            elif match.group(4):  # sum() -> reduce()
                return f"[{match.group(4)}].reduce((a, b) => a + b, 0)"

        return self.branch_logic_pattern.sub(replace_func, condition_str)

    def create_activity_schema(
        self,
        activity_name: str,
        activity_data: Dict[str, Any],
        output_path: Path,
        redcap_version: str,
    ):
        json_ld = {
            "category": "reproschema:Activity",
            "id": f"{activity_name}_schema",
            "prefLabel": {"en": activity_name},
            "schemaVersion": get_context_version(CONTEXTFILE_URL),
            "version": redcap_version,
            "ui": {
                "order": activity_data["order"],
                "addProperties": [
                    {
                        "variableName": item["id"],
                        "isAbout": f"items/{item['id']}",
                        "valueRequired": item.get("valueRequired", False),
                        "isVis": "@HIDDEN" not in item.get("annotation", ""),
                    }
                    for item in activity_data["items"]
                ],
                "shuffle": False,
            },
        }

        if activity_data["compute"]:
            json_ld["compute"] = activity_data["compute"]

        act = Activity(**json_ld)
        path = output_path / "activities" / activity_name
        path.mkdir(parents=True, exist_ok=True)
        file_path = path / f"{activity_name}_schema"
        write_obj_jsonld(act, file_path, contextfile_url=CONTEXTFILE_URL)

        for item in activity_data["items"]:
            it = Item(**item)
            file_path_item = path / "items" / item["id"]
            file_path_item.parent.mkdir(
                parents=True, exist_ok=True
            )  # Create parent directories
            write_obj_jsonld(
                it, file_path_item, contextfile_url=CONTEXTFILE_URL
            )
            print(f"{activity_name} Instrument schema created")

    def create_protocol_schema(
        self,
        protocol_name: str,
        protocol_data: Dict[str, Any],
        activities: List[str],
        output_path: Path,
    ):
        protocol_schema = {
            "category": "reproschema:Protocol",
            "id": f"{protocol_name}_schema",
            "prefLabel": {"en": protocol_data["protocol_display_name"]},
            "description": {
                "en": protocol_data.get("protocol_description", "")
            },
            "schemaVersion": get_context_version(CONTEXTFILE_URL),
            "version": protocol_data["redcap_version"],
            "ui": {
                "addProperties": [
                    {
                        "isAbout": f"../activities/{activity}/{activity}_schema",
                        "variableName": f"{activity}_schema",
                        "prefLabel": {
                            "en": activity.replace("_", " ").title()
                        },
                        "isVis": True,
                    }
                    for activity in activities
                ],
                "order": [
                    f"../activities/{activity}/{activity}_schema"
                    for activity in activities
                ],
                "shuffle": False,
            },
        }

        prot = Protocol(**protocol_schema)
        protocol_dir = output_path / protocol_name
        protocol_dir.mkdir(parents=True, exist_ok=True)
        file_path = protocol_dir / f"{protocol_name}_schema"
        write_obj_jsonld(prot, file_path, contextfile_url=CONTEXTFILE_URL)
        print(f"Protocol schema created in {file_path}")

    def convert(self, csv_file: str, output_path: str):
        try:
            df = self.load_csv(csv_file)
            activities = self.process_dataframe(df)

            abs_output_path = Path(output_path) / self.config[
                "protocol_name"
            ].replace(" ", "_")
            abs_output_path.mkdir(parents=True, exist_ok=True)

            for activity_name, activity_data in activities.items():
                self.create_activity_schema(
                    activity_name,
                    activity_data,
                    abs_output_path,
                    self.config["redcap_version"],
                )

            self.create_protocol_schema(
                self.config["protocol_name"],
                self.config,
                list(activities.keys()),
                abs_output_path,
            )
        except Exception as e:
            print(f"An error occurred during conversion: {str(e)}")
            raise


def main():
    parser = argparse.ArgumentParser(
        description="Convert a CSV file to ReproSchema format."
    )
    parser.add_argument("csv_file", help="Path to the input CSV file.")
    parser.add_argument(
        "config_file", help="Path to the YAML configuration file."
    )
    parser.add_argument(
        "output_path",
        help="Path to the directory where the output schemas will be saved.",
    )

    args = parser.parse_args()

    config = load_config(args.config_file)
    converter = ReproSchemaConverter(config)
    converter.convert(args.csv_file, args.output_path)


if __name__ == "__main__":
    main()
