import json
from . import Protocol, Activity, Item


def load_schema(filepath):
    with open(filepath) as fp:
        data = json.load(fp)
    if "@type" not in data:
        raise ValueError("Missing @type key")
    schema_type = data["@type"]
    if schema_type == "reproschema:Protocol":
        return Protocol.from_data(data)
    if schema_type == "reproschema:Activity":
        return Activity.from_data(data)
    if schema_type == "reproschema:Item":
        return Item.from_data(data)
