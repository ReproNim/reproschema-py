from .base import SchemaBase

DEFAULT_LANG = "en"


class Activity(SchemaBase):
    """
    class to deal with reproschema activities
    """

    schema_type = "reproschema:Activity"

    visible = True
    required = False
    skippable = True

    def __init__(self, version=None):
        super().__init__(version)

    def set_defaults(self, name="default"):
        self._SchemaBase__set_defaults(name)
        self.set_preamble()
        self.set_ui_default()

    def set_compute(self, variable, expression):
        self.schema["compute"] = [
            {"variableName": variable, "jsExpression": expression}
        ]

    def append_item(self, item):

        property = {
            "variableName": item.get_basename(),
            "isAbout": item.get_URI(),
            "isVis": item.visible,
            "requiredValue": item.required,
        }
        if item.skippable:
            property["allow"] = ["reproschema:Skipped"]

        self.schema["ui"]["order"].append(item.get_URI())
        self.schema["ui"]["addProperties"].append(property)

    """
    writing, reading, sorting, unsetting
    """

    def sort(self):
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
        self.sort_schema(schema_order)
        self.sort_ui()

    def write(self, output_dir):
        self.sort()
        self._SchemaBase__write(output_dir)
