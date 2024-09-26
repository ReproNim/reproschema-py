import argparse
import os
import re
import shutil
import warnings
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import yaml
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning

from .context_url import CONTEXTFILE_URL
from .jsonldutils import get_context_version
from .mappings import (
    ADDITIONAL_NOTES_LIST,
    CSV_TO_REPROSCHEMA_MAP,
    INPUT_TYPE_MAP,
    VALUE_TYPE_MAP,
)
from .models import Activity, Item, Protocol, write_obj_jsonld

warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)


def load_config(config_file: str) -> Dict[str, Any]:
    with open(config_file, "r") as f:
        return yaml.safe_load(f)


class ReproSchemaConverter:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.branch_logic_pattern = re.compile(
            r"\[([^\]]+)\]|\b(AND|OR)\b|([^><!=])=|sum\(([^)]+)\)"
        )

    def load_csv(self, csv_file: str) -> pd.DataFrame:
        df = pd.read_csv(csv_file)
        df.columns = df.columns.str.strip().str.replace('"', "")
        return self.preprocess_fields(df)

    def preprocess_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        special_fields = [
            col
            for col in df.columns
            if col.endswith(("_Validity", "_Administration", "_Informant"))
        ]
        for field in special_fields:
            df[field] = df[field].apply(
                lambda x: (
                    x.replace("&gt;", ">").replace("\n", "").replace("\r", "")
                    if isinstance(x, str)
                    else x
                )
            )
        return df

    def process_response_options(
        self, response_option_str: str, item_name: str
    ) -> tuple:
        if pd.isna(response_option_str):
            return [], ["xsd:string"]

        choices = []
        value_types = set()

        if item_name.endswith(("_Validity", "_Administration", "_Informant")):
            pattern = r"''([^']+)'(?:=>|=&gt;)'([^']+)''"
            matches = re.findall(pattern, response_option_str)
            choices = [
                {"name": {"en": name}, "value": value}
                for value, name in matches
            ]
        else:
            for choice in response_option_str.split("{-}"):
                choice = choice.strip()
                if "=>" in choice:
                    value, name = map(
                        lambda x: x.strip("'").strip('"'), choice.split("=>")
                    )
                    choices.append(
                        {
                            "name": {"en": name},
                            "value": (
                                None if value.lower() == "null" else value
                            ),
                        }
                    )
                elif choice != "NULL=>''":
                    print(
                        f"Warning: Unexpected choice format '{choice}' in {item_name} field"
                    )

        if not choices:
            print(f"Warning: No valid choices found for {item_name}")
            choices.append({"name": {"en": "No valid choices"}, "value": None})

        value_types.add("xsd:string")
        return choices, list(value_types)

    def clean_html(self, raw_html: str) -> str:
        if pd.isna(raw_html):
            return ""
        text = str(raw_html)
        if "<" in text and ">" in text:
            return BeautifulSoup(text, "html.parser").get_text()
        return text

    def process_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        item_data = {
            "category": "reproschema:Item",
            "id": item[CSV_TO_REPROSCHEMA_MAP["item_name"]],
            "prefLabel": {"en": item[CSV_TO_REPROSCHEMA_MAP["item_name"]]},
            "question": {
                "en": self.clean_html(item[CSV_TO_REPROSCHEMA_MAP["question"]])
            },
            "ui": {
                "inputType": INPUT_TYPE_MAP.get(
                    item[CSV_TO_REPROSCHEMA_MAP["inputType"]], "text"
                )
            },
            "responseOptions": {
                "valueType": [
                    VALUE_TYPE_MAP.get(
                        str(
                            item.get(
                                CSV_TO_REPROSCHEMA_MAP.get("validation", ""),
                                "",
                            )
                        ).strip(),
                        "xsd:string",
                    )
                ],
                "multipleChoice": item[CSV_TO_REPROSCHEMA_MAP["inputType"]]
                == "Multi-select",
            },
        }

        if CSV_TO_REPROSCHEMA_MAP["response_option"] in item:
            (
                item_data["responseOptions"]["choices"],
                item_data["responseOptions"]["valueType"],
            ) = self.process_response_options(
                item[CSV_TO_REPROSCHEMA_MAP["response_option"]],
                item[CSV_TO_REPROSCHEMA_MAP["item_name"]],
            )

        item_data["additionalNotesObj"] = [
            {"source": "redcap", "column": column, "value": item[column]}
            for column in ADDITIONAL_NOTES_LIST
            if column in item and item[column]
        ]

        return item_data

    def process_dataframe(self, df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        activities = {}
        for activity_name, group in df.groupby(
            CSV_TO_REPROSCHEMA_MAP["activity_name"]
        ):
            items = [
                self.process_item(item) for item in group.to_dict("records")
            ]
            activities[activity_name] = {
                "items": items,
                "order": [f"items/{item['id']}" for item in items],
                "compute": [
                    {"variableName": item["id"], "jsExpression": ""}
                    for item in items
                    if "_score" in item["id"].lower()
                    or item["id"].lower().endswith("_raw")
                ],
            }
        return activities

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
                        "isVis": not (
                            "_score" in item["id"].lower()
                            or item["id"].lower().endswith("_raw")
                            or "@HIDDEN" in item.get("annotation", "").lower()
                        ),
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
        write_obj_jsonld(
            act,
            path / f"{activity_name}_schema",
            contextfile_url=CONTEXTFILE_URL,
        )

        items_path = path / "items"
        items_path.mkdir(parents=True, exist_ok=True)

        for item in activity_data["items"]:
            item_path = items_path / item["id"]
            item_path.parent.mkdir(parents=True, exist_ok=True)
            write_obj_jsonld(
                Item(**item), item_path, contextfile_url=CONTEXTFILE_URL
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

        protocol_dir = output_path / protocol_name
        protocol_dir.mkdir(parents=True, exist_ok=True)
        write_obj_jsonld(
            Protocol(**protocol_schema),
            protocol_dir / f"{protocol_name}_schema",
            contextfile_url=CONTEXTFILE_URL,
        )
        print(f"Protocol schema created in {protocol_dir}")

    def clean_output_directories(self, output_path: Path):
        """Remove only the folders in the output directory."""
        if output_path.exists():
            for item in output_path.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                    print(f"Removed directory: {item}")
            print(f"Cleaned folders in output directory: {output_path}")
        else:
            print(
                f"Output directory does not exist, will be created: {output_path}"
            )

    def remove_ds_store(self, directory: Path):
        """Remove all .DS_Store files in the given directory and its subdirectories."""
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file == ".DS_Store":
                    file_path = Path(root) / file
                    file_path.unlink()
                    print(f"Removed .DS_Store file: {file_path}")

    def convert(self, csv_file: str, output_path: str):
        try:
            df = self.load_csv(csv_file)
            activities = self.process_dataframe(df)

            abs_output_path = Path(output_path) / self.config[
                "protocol_name"
            ].replace(" ", "_")

            # Clean only the folders in the output directory before conversion
            self.clean_output_directories(abs_output_path)

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

            # Remove .DS_Store files after conversion
            self.remove_ds_store(abs_output_path)
            print("Conversion completed and .DS_Store files removed.")
        except Exception as e:
            print(f"An error occurred during conversion: {str(e)}")
            import traceback

            traceback.print_exc()
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
