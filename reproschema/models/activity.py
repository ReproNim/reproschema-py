from .base import SchemaBase
from .item import Item

DEFAULT_LANG = "en"

schema_order = [
    "@context",
    "@type",
    "@id",
    "prefLabel",
    "description",
    "schemaVersion",
    "version",
    "preamble",
    "citation",
    "image",
    "compute",
    "ui",
]


class Activity(SchemaBase):
    """
    class to deal with reproschema activities
    """

    def __init__(
        self,
        name="activity",
        schemaVersion=None,
        suffix="_schema",
        ext=".jsonld",
        visible: bool = True,
        required: bool = False,
        skippable: bool = True,
    ):
        super().__init__(
            at_id=name,
            schemaVersion=schemaVersion,
            type="reproschema:Activity",
            schema_order=schema_order,
            suffix=suffix,
            ext=ext,
        )
        self.visible = visible
        self.required = required
        self.skippable = skippable

    def set_defaults(self, name=None):
        if not name:
            name = self.at_id
        super().set_defaults(name)
        self.set_preamble(name)
        self.set_ui_default()

    def set_compute(self, variable, expression):
        self.schema["compute"] = [
            {"variableName": variable, "jsExpression": expression}
        ]

    def append_item(self, item: Item):
        item_property = {
            "variableName": item.get_basename(),
            "isAbout": item.URI,
            "isVis": item.visible,
            "requiredValue": item.required,
        }
        self.append_to_ui(item, item_property)

    """
    writing, reading, sorting, unsetting
    """

    def write(self, output_dir):
        self.sort()
        self._SchemaBase__write(output_dir)
