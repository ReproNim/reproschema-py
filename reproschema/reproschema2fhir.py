import re as r
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path


def add_enable_when(condition: str):
    """
    Parses condition string and returns the enablewhen json
    """
    enable_when = []
    behave = "None"
    condition = condition.replace("\n", "")
    if "||" in condition or " or" in condition:
        behave = "any"
    elif "&&" in condition or " and " in condition:
        behave = "all"

    # we are trying to clean up the condition string so we can apply regex to it
    # special characters like '||' is a regex specific character
    condition = condition.replace(" or", " or ")
    condition = condition.replace('"', "")
    condition = condition.replace("||", " or ")
    condition = condition.replace("! == ", "!=")

    condition = r.split(r"&&|and | or ", condition)

    for i in condition:
        # the exact order of the regex matters as otherwise '<' will be parsed instead of '<='
        (id, operator, answer_string) = r.split(r"(==|>=|<=|!=|>|<)", i)
        if operator == "==":
            operator = "="
        # regex to that removes parentheses
        id = r.sub(r"\([^()]*\)", "", id.strip())

        # visibility is based on which button was checked checked
        # eg. current_neuro_dx checks if neurological_history between to 1-6.
        # isVis lists it as neurological_history___{1-6} == 1.
        # We replace the underscores and re-assign question and answerString
        if "___" in id:
            id, answer_string = r.split(r"___+", id)
        enable_when.append(
            {
                "question": id.strip(),
                "operator": operator.strip(),
                "answerString": answer_string.strip(),
            }
        )

    return (enable_when, behave)


def add_options(options_json) -> list:
    """
    Helper function to extract all answer choices to a list
    """
    options = []
    for j in options_json["choices"]:
        if "schema:name" in j and j["schema:name"] != "":
            choice = j["schema:name"]
        elif "name" in j and j["name"] != "":
            choice = j["name"]
            if "en" in j["name"] and isinstance(["name"], dict):
                choice = choice["en"]
            else:
                pass
        elif "schema:value" in j:
            choice = j["schema:value"]
        else:
            choice = j["value"]

        if (
            choice
            and not isinstance(choice, int)
            and "en" in choice
            and isinstance(choice, dict)
        ):
            choice = choice["en"]

        choice = str(choice).strip()
        if choice != "":
            options.append(choice)
    return options


def parse_reproschema_items(
    reproschema_items: OrderedDict, reproschema_content: OrderedDict
):
    """
    Helper function to parse reproschema items into fhir items

    Example of reproschema_items content:

    {
        "items/1": {
            "@id": "items/1",
            ...
        },
        "items/2": {
            "@id": "items/2",
            ...
        },
        ...
    }
    """
    # there are a few possibilities for responses presented by reproschema:
    # 1. responseOptions is a string, which is a reference to a file with the responses
    # 2. responseOptions is a dict, which is a list of options
    items = []
    schema_name = [
        name
        for name in list(reproschema_content.keys())
        if name.endswith("_schema")
    ][0]
    question_visibility = dict()

    reproschema_schema_properties = reproschema_content[schema_name]["ui"][
        "addProperties"
    ]
    for property in reproschema_schema_properties:
        question_visibility[property["variableName"]] = property["isVis"]

    for item_path, item_json in reproschema_items.items():
        curr_item = dict()

        var_name = item_path.replace("items/", "")
        curr_item["linkId"] = var_name

        item_type = "string"
        if "inputType" in item_json["ui"]:
            if item_json["ui"]["inputType"] == "radio":
                item_type = "choice"
            elif item_json["ui"]["inputType"] in ("number", "xsd:int"):
                item_type = "integer"
            elif item_json["ui"]["inputType"] in (
                "audioImageRecord",
                "audioRecord",
            ):
                item_type = "attachment"
            else:
                item_type = "string"

        curr_item["type"] = item_type
        preamble = ""
        if "preamble" in item_json and isinstance(item_json["preamble"], dict):
            preamble = item_json["preamble"]["en"]
        elif "preamble" in item_json and isinstance(
            item_json["preamble"], str
        ):
            preamble = item_json["preamble"]

        if preamble != "":
            preamble = f"{preamble}: "

        if "question" in item_json and isinstance(item_json["question"], dict):
            curr_item["text"] = preamble + str(item_json["question"]["en"])

        elif "prefLabel" in item_json:
            curr_item["text"] = str(item_json["prefLabel"])
        else:
            curr_item["text"] = curr_item["linkId"]

        id_str: str = var_name
        id_str = id_str.replace("_", "-")
        id_str = id_str.lower()

        if "responseOptions" in item_json:
            if isinstance(item_json["responseOptions"], str):
                # resolve the path relative to the items folder to load in the dict
                options_path = (
                    Path(item_path).parent / item_json["responseOptions"]
                )
                options_path = options_path.resolve()

                options_json = reproschema_content[
                    (str(options_path)).split("/")[-1]
                ]

                options = add_options(options_json)

                curr_item["linkId"] = var_name
                curr_item["type"] = "string"
                if "question" in item_json:
                    curr_item["text"] = preamble + str(
                        item_json["question"]["en"]
                    )
                else:
                    curr_item["text"] = preamble
                curr_item["answerOption"] = [
                    {"valueString": option.strip()} for option in options
                ]
                # VERSION 0.0.1
            elif isinstance(item_json["responseOptions"], dict):
                if (
                    "choices" not in item_json["responseOptions"]
                    or item_json["responseOptions"]["choices"] is None
                ):
                    curr_item["linkId"] = var_name
                    if (
                        "valueType" in item_json["responseOptions"]
                        and "int" in item_json["responseOptions"]["valueType"]
                    ):
                        curr_item["type"] = "integer"
                    elif (
                        "valueType" in item_json["responseOptions"]
                        and "date" in item_json["responseOptions"]["valueType"]
                    ):
                        curr_item["type"] = "date"
                    elif (
                        "valueType" in item_json["responseOptions"]
                        and "audio"
                        in item_json["responseOptions"]["valueType"]
                    ):
                        curr_item["type"] = "attachment"
                    else:
                        curr_item["type"] = "string"
                    if "question" not in item_json:
                        if "prefLabel" in item_json:
                            curr_item["text"] = preamble + str(
                                item_json["prefLabel"]
                            )
                        else:
                            curr_item["text"] = preamble + curr_item["linkId"]
                    else:
                        curr_item["text"] = preamble + str(
                            item_json["question"]["en"]
                        )

                elif "choices" in item_json["responseOptions"]:
                    options_json = item_json["responseOptions"]
                    options = add_options(options_json)

                    curr_item["linkId"] = var_name
                    curr_item["type"] = "choice"
                    if "question" in item_json:
                        curr_item["text"] = preamble + str(
                            item_json["question"]["en"]
                        )
                    else:
                        curr_item["text"] = preamble
                    curr_item["answerOption"] = [
                        {"valueString": option.strip()} for option in options
                    ]

        if curr_item["linkId"] in question_visibility and isinstance(
            question_visibility[curr_item["linkId"]], str
        ):
            isVis = question_visibility[curr_item["linkId"]]
            (enable_when, behave) = add_enable_when(isVis)
            curr_item["enableWhen"] = enable_when
            if behave != "None":
                curr_item["enableBehavior"] = behave

        items.append(curr_item)
    return items


def convert_to_fhir(reproschema_content: dict):
    """
    Function used to convert reproschema questionnaire into a fhir json

    Input is a dictionary which maps file: dict, where the dict is the loaded in
    jsonld file.
    """
    fhir_questionnaire = dict()

    # reference to the main schema file
    schema_name = [
        name
        for name in list(reproschema_content.keys())
        if name.endswith("_schema")
    ][0]
    reproschema_schema = reproschema_content[schema_name]
    # reproschema can have id defined with either @id or id
    id_value = "@id" if "@id" in reproschema_schema else "id"

    reproschema_id = (reproschema_schema[id_value]).replace("_", "")

    # create fhir questionnaire
    fhir_questionnaire["resourceType"] = "Questionnaire"
    fhir_questionnaire["id"] = reproschema_id
    fhir_questionnaire["title"] = reproschema_schema[id_value]

    fhir_questionnaire["version"] = "1.4.0"
    fhir_questionnaire["status"] = "active"
    fhir_questionnaire["date"] = (datetime.now(timezone.utc)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    # create a pointer to the reproschema_items jsons and match the question
    reproschema_items = OrderedDict(
        [
            (i, value)
            for (i, value) in reproschema_content.items()
            if i.startswith("items/")
        ]
    )

    question_order = [
        ("items/" + sub.replace("items/", ""))
        for sub in reproschema_schema["ui"]["order"]
    ]

    reproschema_items = OrderedDict(
        (key, reproschema_items[key]) for key in question_order
    )

    items = parse_reproschema_items(reproschema_items, reproschema_content)

    fhir_questionnaire["item"] = items
    return fhir_questionnaire
