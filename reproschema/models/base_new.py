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
    schema = field(default={
        "@context": "https://raw.githubusercontent.com/ReproNim/reproschema//contexts/generic",
        "@type": 'None',
    })
    # order = attr.ib(validator=attr.validators.deep_iterable(
    #     member_validator = attr.validators.instance_of(str),
    #     iterable_validator = attr.validators.instance_of(list)
    # ))

    # def set_filename(self, name):
    #     self.schema_file = name + "_schema"
    #     self.schema["@id"] = name + "_schema"

    def get_name(self):
        return self.schema_file.replace("_schema", "")

    def get_filename(self):
        return self.schema_file

    def __set_defaults(self, name):
        self.set_filename(name)
        self.set_directory(name)
        self.set_pref_label(name.replace("_", " "))
        self.set_description(name.replace("_", " "))  # description isn't mandatory, no?

    def sort_schema(self, schema_order):

        reordered_dict = {k: self.schema[k] for k in schema_order}
        self.schema = reordered_dict

    def sort_ui(self, ui_order):

        reordered_dict = {k: self.schema["ui"][k] for k in ui_order}
        self.schema["ui"] = reordered_dict

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


# aa = SchemaBase(prefLabel="ann", description='trial')
# print('------------')
# print(12, aa.__dict__.keys())
# props = aa.__dict__.copy()
# # del props['schema']
# # print(13, props)
# print(aa.write('./', 'tt_schema'))
