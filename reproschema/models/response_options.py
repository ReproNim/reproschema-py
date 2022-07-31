from .base import SchemaBase

DEFAULT_LANG = "en"

options_order = [
    "@context",
    "@type",
    "@id",
    "valueType",
    "minValue",
    "maxValue",
    "multipleChoice",
    "choices",
]


class ResponseOption(SchemaBase):
    """
    class to deal with reproschema response options
    """

    # the dictionary that keeps track of the content of the response options should
    # be called "schema" and not "options" so as to be able to make proper use of the
    # methods of the parent class and avoid copying content between
    #
    # self.options and self.schema

    def __init__(self, name="valueConstraints", schemaVersion=None):
        super().__init__(
            at_id=name,
            schema_order=options_order,
            schemaVersion=schemaVersion,
            type="reproschema:ResponseOption",
            ext=".jsonld",
            suffix="",
        )
        self.options = {
            "valueType": "",
            "minValue": 0,
            "maxValue": 0,
            "choices": [],
            "multipleChoice": False,
        }

    def set_defaults(self):
        self.options["@context"] = self.schema["@context"]
        self.options["@type"] = self.type
        self.set_filename(self.at_id)

    def set_filename(self, name: str):
        super().set_filename(name)
        self.options["@id"] = self.at_id

    def unset(self, keys):
        if type(keys) == str:
            keys = [keys]
        for i in keys:
            self.options.pop(i, None)

    def set_type(self, type):
        self.options["valueType"] = f"xsd:{type}"

    # TODO a nice thing to do would be to read the min and max value
    # from the rest of the content of self.options
    # could avoid having the user to input those
    def set_min(self, value):
        self.options["minValue"] = value

    def set_max(self, value):
        self.options["maxValue"] = value

    def set_length(self, value):
        self.options["maxLength"] = value

    def set_multiple_choice(self, value):
        self.options["multipleChoice"] = value

    def use_preset(self, URI):
        """
        In case the list response options are read from another file
        like for languages, country, state...
        """
        self.options["choices"] = URI

    def add_choice(self, choice, value, lang=DEFAULT_LANG):
        self.options["choices"].append({"name": {lang: choice}, "value": value})

    def sort(self):
        reordered_dict = self.reorder_dict_skip_missing(self.options, self.schema_order)
        self.options = reordered_dict

    def write(self, output_dir):
        self.sort()
        self.schema = self.options
        self._SchemaBase__write(output_dir)
