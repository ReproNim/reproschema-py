from .base import SchemaBase

DEFAULT_LANG = "en"


class Protocol(SchemaBase):
    """
    class to deal with reproschema protocols
    """

    schema_type = "reproschema:Protocol"

    def __init__(self, version=None):
        """
        Rely on the parent class for construction of the instance
        """
        super().__init__(version)

    def set_defaults(self, name="default"):
        self._SchemaBase__set_defaults(name)
        self.set_landing_page("README-en.md")
        # does it make sense to give a preamble by default to protocols since
        # they already have a landing page?
        self.set_preamble()
        self.set_ui_default()

    def set_landing_page(self, landing_page_uri, lang=DEFAULT_LANG):
        self.schema["landingPage"] = {"@id": landing_page_uri, "inLanguage": lang}

    def append_activity(self, activity):
        """
        We get from an activity instance the info we need to update the protocol scheme.

        This appends the activity after all the other ones.

        So this means the order of the activities will be dependent
        on the order in which they are "read".

        This implementation assumes that the activities are read
        from a list and added one after the other.
        """
        # TODO
        # - find a way to reorder, remove or add an activity
        # at any point in the protocol
        # - this method is nearly identical to the append_item method of Activity
        # and should probably be refactored into a single method of the parent class
        # and ideally into a method of a yet to be created UI class

        property = {
            # variable name is name of activity without prefix
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
