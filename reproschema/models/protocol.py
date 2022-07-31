from .activity import Activity
from .base import SchemaBase


DEFAULT_LANG = "en"

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


class Protocol(SchemaBase):
    """
    class to deal with reproschema protocols
    """

    def __init__(
        self,
        name="protocol",
        schemaVersion=None,
        prefLabel="protocol",
        suffix="_schema",
        ext=".jsonld",
        lang=DEFAULT_LANG,
    ):
        """
        Rely on the parent class for construction of the instance
        """
        super().__init__(
            at_id=name,
            schemaVersion=schemaVersion,
            type="reproschema:Protocol",
            prefLabel={lang: prefLabel},
            schema_order=schema_order,
            suffix=suffix,
            ext=ext,
            lang=lang,
        )

    def set_defaults(self, name=None):
        if not name:
            name = self.at_id
        super().set_defaults(name)
        self.set_landing_page("README-en.md")
        self.set_preamble(name)
        self.set_ui_default()

    def set_landing_page(self, landing_page_uri: str, lang=DEFAULT_LANG):
        self.schema["landingPage"] = {"@id": landing_page_uri, "inLanguage": lang}

    def append_activity(self, activity: Activity):
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

        activity_property = {
            # variable name is name of activity without prefix
            "variableName": activity.get_basename().replace("_schema", ""),
            "isAbout": activity.URI,
            "prefLabel": activity.prefLabel,
            "isVis": activity.visible,
            "requiredValue": activity.required,
        }
        self.append_to_ui(activity, activity_property)

    """
    writing, reading, sorting, unsetting
    """

    def write(self, output_dir):
        self.sort()
        self._SchemaBase__write(output_dir)
