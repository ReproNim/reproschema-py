import json

from .model import (
    Activity,
    Item,
    Protocol,
    Response,
    ResponseActivity,
    ResponseOption,
)


def identify_model_class(category):
    if (
        category == "http://schema.repronim.org/Field"
        or category == "http://schema.repronim.org/Item"
    ):
        model_class = Item
    elif category == "http://schema.repronim.org/ResponseOption":
        model_class = ResponseOption
    elif category == "http://schema.repronim.org/Activity":
        model_class = Activity
    elif category == "http://schema.repronim.org/Protocol":
        model_class = Protocol
    elif category == "http://schema.repronim.org/ResponseActivity":
        model_class = ResponseActivity
    elif category == "http://schema.repronim.org/Response":
        model_class = Response
    else:
        raise ValueError(f"Unknown type: {category}")
    return model_class


def write_obj_jsonld(model_obj, path, contextfile_url=None):
    """Write a pydantic model object to a jsonld file."""
    # TODO: perhaps automatically should take contextfile
    model_dict = model_obj.model_dump(
        exclude_unset=True,
    )
    model_dict["@context"] = contextfile_url

    with open(path, "w") as f:
        json.dump(model_dict, f, indent=4)
    return path
