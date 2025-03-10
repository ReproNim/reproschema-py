import re
from pathlib import Path
from typing import Any, Dict, List

import yaml
from bs4 import BeautifulSoup

from .context_url import CONTEXTFILE_URL
from .jsonldutils import get_context_version
from .models import Activity, Item, Protocol, write_obj_jsonld

PROTOCOL_KEYS_REQUIRED = [
    "protocol_name",
    "protocol_display_name",
    "redcap_version",
]


def read_check_yaml_config(yaml_path: str) -> Dict[str, Any]:
    """Read and check the YAML configuration file."""
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            protocol = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML file: {str(e)}")
    if set(PROTOCOL_KEYS_REQUIRED) - set(protocol.keys()):
        raise ValueError(
            f"Missing required keys in YAML file: {set(PROTOCOL_KEYS_REQUIRED) - set(protocol.keys())}"
        )
    return protocol


def normalize_condition(condition_str, field_type=None):
    """Normalize condition strings with specific handling for calc fields."""

    # Handle boolean values
    if isinstance(condition_str, bool):
        return condition_str
    if isinstance(condition_str, str):
        if condition_str.lower() == "true":
            return True
        if condition_str.lower() == "false":
            return False

    # Convert to string if needed
    if not isinstance(condition_str, str):
        try:
            condition_str = str(condition_str)
        except:
            raise ValueError("Condition must be a string or boolean")

    # Clean HTML
    condition_str = BeautifulSoup(condition_str, "html.parser").get_text()
    condition_str = condition_str.strip()

    if condition_str is None:
        return None

    # Common operator normalizations for all types
    operator_replacements = [
        (r"\s*\+\s*", " + "),  # Normalize spacing around +
        (r"\s*-\s*", " - "),  # Normalize spacing around -
        (r"\s*\*\s*", " * "),  # Normalize spacing around *
        (r"\s*\/\s*", " / "),  # Normalize spacing around /
        (r"\s*\(\s*", "("),  # Remove spaces after opening parenthesis
        (r"\s*\)\s*", ")"),  # Remove spaces before closing parenthesis
        (r"\s*,\s*", ","),  # Normalize spaces around commas
        (r"\s+", " "),  # Normalize multiple spaces
    ]

    # Apply operator normalizations first
    for pattern, repl in operator_replacements:
        condition_str = re.sub(pattern, repl, condition_str)

    # Then apply type-specific replacements
    if field_type in ["sql", "calc"]:
        # For calc fields, just remove brackets from field references
        condition_str = re.sub(r"\[([^\]]+)\]", r"\1", condition_str)
    else:
        # For branching logic
        replacements = [
            (r"\(([0-9]*)\)", r"___\1"),
            (r"([^>|<])=", r"\1=="),
            (r"\[([^\]]*)\]", r"\1"),  # Remove brackets and extra spaces
            (r"\bor\b", "||"),
            (r"\band\b", "&&"),
            (r'"', "'"),
        ]
        for pattern, repl in replacements:
            condition_str = re.sub(pattern, repl, condition_str)

    result = condition_str.strip()
    return result


def parse_html(input_string, default_language="en"):
    """
    Parse HTML content and extract language-specific text.

    Args:
        input_string: The HTML string to parse
        default_language: Default language code (default: "en")

    Returns:
        dict: Dictionary of language codes to text content, or None if invalid
    """
    try:
        result = {}

        # Handle non-string input
        if not isinstance(input_string, str):
            try:
                input_string = str(input_string)
            except:
                return None

        # Clean input string
        input_string = input_string.strip()
        if not input_string:
            return None

        # Parse HTML
        soup = BeautifulSoup(input_string, "html.parser")

        # Find elements with lang attribute
        lang_elements = soup.find_all(True, {"lang": True})

        if lang_elements:
            # Process elements with language tags
            for element in lang_elements:
                lang = element.get("lang", default_language).lower()
                text = element.get_text(strip=True)
                if text:
                    result[lang] = text

            # If no text was extracted but elements exist, try getting default text
            if not result:
                text = soup.get_text(strip=True)
                if text:
                    result[default_language] = text
        else:
            # No language tags found, use default language
            text = soup.get_text(strip=True)
            if text:
                result[default_language] = text

        return result if result else None

    except Exception as e:
        print(f"Error parsing HTML: {str(e)}, trying plain text")
        # Try to return plain text if HTML parsing fails
        try:
            if isinstance(input_string, str) and input_string.strip():
                return {default_language: input_string.strip()}
        except:
            raise ValueError(f"Invalid input for HTML parsing: {input_string}")


def create_activity_schema(
    activity_name: str,
    activity_data: Dict[str, Any],
    output_path: Path,
    redcap_version: str,
    contextfile_url: str = CONTEXTFILE_URL,
):
    json_ld = {
        "category": "reproschema:Activity",
        "id": f"{activity_name}_schema",
        "prefLabel": {"en": activity_name},
        "schemaVersion": get_context_version(contextfile_url),
        "version": redcap_version,
        "ui": {
            "order": activity_data[
                "order"
            ],  # TODO spr czy to jest "clean order" i "clean bl list"?
            "addProperties": activity_data["addProperties"],
            "shuffle": False,
        },
    }

    if activity_data["compute"]:
        json_ld["compute"] = activity_data["compute"]
    if activity_data.get("preamble"):
        json_ld["preamble"] = activity_data["preamble"]
    act = Activity(**json_ld)
    path = output_path / "activities" / activity_name
    path.mkdir(parents=True, exist_ok=True)
    write_obj_jsonld(
        act,
        path / f"{activity_name}_schema",
        contextfile_url=contextfile_url,
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
    protocol_data: Dict[str, Any],
    activities: List[str],
    output_path: Path,
    contextfile_url: str = CONTEXTFILE_URL,
):
    protocol_name = protocol_data["protocol_name"].strip().replace(" ", "_")
    protocol_schema = {
        "category": "reproschema:Protocol",
        "id": f"{protocol_name}_schema",
        "prefLabel": {"en": protocol_data["protocol_display_name"]},
        "description": {"en": protocol_data.get("protocol_description", "")},
        "schemaVersion": get_context_version(contextfile_url),
        "version": protocol_data["redcap_version"],
        "ui": {
            "addProperties": [
                {
                    "isAbout": f"../activities/{activity}/{activity}_schema",
                    "variableName": f"{activity}_schema",
                    "prefLabel": {"en": activity.replace("_", " ").title()},
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
        contextfile_url=contextfile_url,
    )
    print(f"Protocol schema created in {protocol_dir}")
