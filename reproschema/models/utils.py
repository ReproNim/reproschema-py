import json
from .model import Protocol, Activity, Item, ResponseOption


# TODO: where can we be used?
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


def write_obj_jsonld(model_obj, path):
    """Write a pydantic model object to a jsonld file."""
    contextfile = "https://raw.githubusercontent.com/djarecka/reproschema/linkml_new_tmp/contexts/reproschema_new"
    model_dict = model_obj.model_dump(
        exclude_unset=True,
    )
    model_dict["@context"] = contextfile

    with open(path, "w") as f:
        json.dump(model_dict, f, indent=4)
    return path
