from .base import SchemaBase

DEFAULT_LANG = "en"


class Protocol(SchemaBase):
    """
    class to deal with reproschema protocols
    """

    schema_type = "reproschema:Protocol"

    def __init__(self, version=None):
        super().__init__(version)
        self.schema["ui"] = {
            "allow": [],
            "shuffle": [],
            "order": [],
            "addProperties": [],
        }

    def set_defaults(self, name="default"):
        self._SchemaBase__set_defaults(name)
        self.set_landing_page("README-en.md")
        self.set_preamble()
        self.set_ui_default()

    def set_landing_page(self, landing_page_uri, lang=DEFAULT_LANG):
        self.schema["landingPage"] = {"@id": landing_page_uri, "inLanguage": lang}

    def append_activity(self, activity):

        append_to_protocol = {
            "variableName": activity.get_basename().replace("_schema", ""),
            "isAbout": activity.get_URI(),
            "prefLabel": activity.get_pref_label(),
            "isVis": True,
            "valueRequired": False,
        }

        property = {
            "variableName": activity.get_basename().replace("_schema", ""),
            "isAbout": activity.get_URI(),
            "prefLabel": activity.get_pref_label(),
            "isVis": activity.visible,
            "requiredValue": activity.required,
        }
        if activity.skippable:
            property["allow"] = ["reproschema:Skipped"]

        self.schema["ui"]["order"].append(activity.get_URI())
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
            "landingPage",
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
