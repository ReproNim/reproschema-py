import attr
from .base_new import SchemaBase


from attrs import define, field

@define
class Protocol(SchemaBase):
    """
    class to deal with reproschema protocols
    """
    def __attrs_post_init__(self):
        self.schema_type ="reproschema:Protocol"

    # schema_type = attr.ib(default=None, kw_only=True)

    # ui = attr.ib(default={
    #         "allow": attr.ib(default=attr.Factory(list)),
    #         "shuffle": attr.ib(default=False),
    #         "order": attr.ib(default=attr.Factory(list)),
    #         "addProperties": attr.ib(default=attr.Factory(list)),
    #         "overrideProperties": attr.ib(default=attr.Factory(list)),
    # })
    # def __init__(self, version=None):
    #     super().__init__(version)
    #     self.schema["ui"] = {
    #         "allow": [],
    #         "shuffle": [],
    #         "order": [],
    #         "addProperties": [],
    #         "overrideProperties": [],
    #     }

    def set_landing_page(self, landing_page_url, lang="en"):
        self.schema["landingPage"] = {"@id": landing_page_url, "@language": lang}

    # TODO
    # def add_landing_page(self, landing_page_url, lang="en"):
    # preamble
    # compute

    def set_image(self, image_url):
        self.schema["image"] = image_url

    def set_ui_allow(self):
        self.schema["ui"]["allow"] = [
            "reproschema:AutoAdvance",
            "reproschema:AllowExport",
        ]

    # def set_ui_shuffle(self, shuffle=False):
    #     self.schema["ui"]["shuffle"] = shuffle

    def set_defaults(self, name="default"):
        self._SchemaBase__set_defaults(name)
        self.set_landing_page("README-en.md")
        # does it make sense to give a preamble by default to protocols since
        # they already have a landing page?
        self.set_preamble()
        self.set_ui_default()

    def append_activity(self, activity):

        # TODO
        # - remove the hard coding on visibility and valueRequired

        # update the content of the protocol with this new activity
        append_to_protocol = {
            "variableName": activity.get_name(),
            "isAbout": activity.get_URI(),
            "prefLabel": {"en": activity.schema["prefLabel"]},
            "isVis": True,
            "valueRequired": False,
            # schedule, randomMaxDelay, limit
        }

        self.schema["ui"]["order"].append(activity.URI)
        self.schema["ui"]["addProperties"].append(append_to_protocol)

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
            "ui",
        ]
        self.sort_schema(schema_order)

        ui_order = ["allow", "shuffle", "order", "addProperties", "overrideProperties"]
        self.sort_ui(ui_order)

    def write(self, output_dir):
        # self.sort()
        self._SchemaBase__write(output_dir)
