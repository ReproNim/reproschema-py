import json
import os


class SchemaBase:
    """
    class to deal with reproschema schemas
    """

    schema_type = None

    def __init__(self, version):

        URL = "https://raw.githubusercontent.com/ReproNim/reproschema/"
        VERSION = version or "1.0.0-rc2"

        self.schema = {
            "@context": URL + VERSION + "/contexts/generic",
            "@type": self.schema_type,
            "schemaVersion": VERSION,
            "version": "0.0.1",
        }

    def set_filename(self, name):
        self.schema_file = name + "_schema"
        self.schema["@id"] = name + "_schema"

    def get_name(self):
        return self.schema_file.replace("_schema", "")

    def get_filename(self):
        return self.schema_file

    def set_pref_label(self, pref_label):
        self.schema["prefLabel"] = pref_label

    def set_description(self, description):
        self.schema["description"] = description

    def set_directory(self, output_directory):
        self.dir = output_directory

    def __set_defaults(self, name):
        self.set_filename(name)
        self.set_directory(name)
        self.set_pref_label(name.replace("_", " "))
        self.set_description(name.replace("_", " "))

    def sort_schema(self, schema_order):

        reordered_dict = {k: self.schema[k] for k in schema_order}
        self.schema = reordered_dict

    def sort_ui(self, ui_order):

        reordered_dict = {k: self.schema["ui"][k] for k in ui_order}
        self.schema["ui"] = reordered_dict

    def write(self, output_dir):
        with open(os.path.join(output_dir, self.schema_file), "w") as ff:
            json.dump(self.schema, ff, sort_keys=False, indent=4)

    @classmethod
    def from_data(cls, data):
        if cls.schema_type is None:
            raise ValueError("SchemaBase cannot be used to instantiate class")
        if cls.schema_type != data["@type"]:
            raise ValueError(f"Mismatch in type {data['@type']} != {cls.schema_type}")
        klass = cls()
        klass.schema = data
        return klass

    @classmethod
    def from_file(cls, filepath):
        with open(filepath) as fp:
            data = json.load(fp)
        if "@type" not in data:
            raise ValueError("Missing @type key")
        return cls.from_data(data)
