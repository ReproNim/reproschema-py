import json

from typing import Optional

from attrs import define, field
from attrs.validators import instance_of, optional

# SchemaBase = attr.make_class("SchemaBase",
#                              {"prefLabel": attr.ib(kw_only=True, validator=attr.validators.instance_of(str)),
#                               "description": attr.ib(default=None,
#                                                      validator=attr.validators.optional(attr.validators.instance_of(str))),
#                               "schemaVersion": attr.ib(default="1.0.0-rc4", validator=attr.validators.instance_of(str)),
#                               "version": attr.ib(default="0.0.1", validator=attr.validators.instance_of(str)),
#                               "schema_type": attr.ib(default=None, kw_only=True)
#                               })


@define
class SchemaBase:

    DEFAULT_LANG = "en"

    prefLabel: Optional[str] = field(
        default=None, kw_only=True, validator=optional(instance_of(str))
    )
    description: Optional[str] = field(
        default=None, kw_only=True, validator=optional(instance_of(str))
    )
    schemaVersion: Optional[str] = field(
        default="1.0.0-rc4", kw_only=True, validator=instance_of(str)
    )
    version: Optional[str] = field(
        default="0.0.1", kw_only=True, validator=instance_of(str)
    )
    schema_type = field(default=None, kw_only=True)
    schema = field(
        default={
            "@context": "https://raw.githubusercontent.com/ReproNim/reproschema//contexts/generic",
            "@type": "None",
        }
    )
    schema_file = field(default=None)
    directory = field(default=None)

    def set_directory(self, output_directory):
        """
        Where the file will be written by the ``write`` method
        """
        self.directory = output_directory

    # order = attr.ib(validator=attr.validators.deep_iterable(
    #     member_validator = attr.validators.instance_of(str),
    #     iterable_validator = attr.validators.instance_of(list)
    # ))

    def set_filename(self, name, ext=".jsonld"):
        """
        By default all files are given:
          - the ``.jsold`` extension
          - have ``_schema`` suffix appended to them

        For item files their name won't have the schema prefix.
        """
        # TODO figure out if the latter is a desirable behavior
        self.schema_file = name + "_schema" + ext
        self.schema["@id"] = name + "_schema" + ext

    def get_name(self):
        return self.schema_file.replace("_schema", "")

    def get_filename(self):
        return self.schema_file

    def __set_defaults(self, name):
        self.set_filename(name)
        self.set_directory(name)
        self.prefLabel = name.replace("_", " ")
        self.description = name.replace("_", " ")

    def set_ui_default(self):
        self.schema["ui"] = {
            "shuffle": [],
            "order": [],
            "addProperties": [],
            "allow": [],
        }
        self.set_ui_shuffle()
        self.set_ui_allow()

    def set_ui_shuffle(self, shuffle=False):
        self.schema["ui"]["shuffle"] = shuffle

    def set_ui_allow(self, auto_advance=True, allow_export=True, disable_back=False):
        # TODO
        # Could be more convenient to have one method for each property
        #
        # Also currently the way this is handled makes it hard to update a single value:
        # all 3 have to be reset everytime!!!
        #
        # Could be useful to have a UI class with dictionnary content that is only
        #  generated when the file is written
        allow = []
        if auto_advance:
            allow.append("reproschema:AutoAdvance")
        if allow_export:
            allow.append("reproschema:AllowExport")
        if disable_back:
            allow.append("reproschema:DisableBack")
        self.schema["ui"]["allow"] = allow        

    def set_preamble(self, preamble="", lang=DEFAULT_LANG):
        self.schema["preamble"] = {lang: preamble}

    def sort_schema(self, schema_order):

        reordered_dict = {k: self.schema[k] for k in schema_order}
        self.schema = reordered_dict

    def sort_ui(self, ui_order):

        reordered_dict = {k: self.schema["ui"][k] for k in ui_order}
        self.schema["ui"] = reordered_dict

    def __write(self, output_dir):
        """
        Reused by the write method of the children classes
        """
        if isinstance(output_dir, str):
            output_dir = Path(output_dir)
        with open(output_dir.joinpath(self.schema_file), "w") as ff:
            json.dump(self.schema, ff, sort_keys=False, indent=4)        

    # def write(self, output_dir, filename):
    #     # self.schema_file = filename + "_schema"
    #     self.schema["@id"] = filename
    #     props = aa.__dict__.copy()
    #     del props['schema']
    #     props.update(self.schema)
    #     with open(os.path.join(output_dir, filename), "w") as ff:
    #         json.dump(props, ff, sort_keys=True, indent=4)

    @classmethod
    def from_data(cls, data, schema_type=None):
        klass = cls(schema_type=schema_type)
        if klass.schema_type is None:
            raise ValueError("SchemaBase cannot be used to instantiate class")
        if klass.schema_type != data["@type"]:
            raise ValueError(f"Mismatch in type {data['@type']} != {klass.schema_type}")
        klass.schema = data
        return klass

    @classmethod
    def from_file(cls, filepath):
        with open(filepath) as fp:
            data = json.load(fp)
        if "@type" not in data:
            raise ValueError("Missing @type key")
        return cls.from_data(data)
