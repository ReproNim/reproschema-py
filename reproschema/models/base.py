import json
import os
from pathlib import Path
from collections import OrderedDict

"""
For any key that can be 'translated' we set english as the default language
in case the user does not provide it.
"""
DEFAULT_LANG = "en"

"""
"""
DEFAULT_VERSION = "1.0.0-rc4"


def default_context(version):
    """
    For now we assume that the github repo will be where schema will be read from.
    """
    URL = "https://raw.githubusercontent.com/ReproNim/reproschema/"
    VERSION = version or DEFAULT_VERSION
    return URL + VERSION + "/contexts/generic"


class SchemaBase:
    """
    base class to deal with reproschema schemas

    The content of the schema is stored in the dictionnary ``self.schema``

        self.schema["@context"]
        self.schema["@type"]
        self.schema["schemaVersion"]
        self.schema["version"]
        self.schema["preamble"]
        self.schema["citation"]
        self.schema["image"]
        ...

    When the output file is created, its content is simply dumped into a json
    by the ``write`` method.

    """

    # TODO might be more convenient to have some of the properties not centrlized in a single dictionnary
    #
    # Could be more practical to only create part or all of the dictionnary when write is called
    #

    schema_type = None

    def __init__(self, version):

        # TODO the version handling could probably be refactored
        VERSION = version or DEFAULT_VERSION

        self.schema = {
            "@type": self.schema_type,
            "schemaVersion": VERSION,
            "version": "0.0.1",
        }

        URL = self.get_default_context(version)
        self.set_context(URL)

    # This probably needs some cleaning but is at the moment necessary to pass
    # the context to the ResponseOption class
    def get_default_context(self, version):
        return default_context(version)

    def __set_defaults(self, name):
        self.set_filename(name)
        self.set_directory(name)
        "We use the ``name`` of this class instance for schema keys minus some underscore"
        self.set_pref_label(name.replace("_", " "))
        self.set_description(name.replace("_", " "))

    """
        setters
    """

    def set_directory(self, output_directory):
        """
        Where the file will be written by the ``write`` method
        """
        self.dir = output_directory

    def set_URI(self, URI):
        """
        In case we need to keep where the output file is located,
        we can set it with this method.
        This can be useful if we have just read or created an item
        and want to add it to an activity.
        """
        self.URI = URI

    """
        schema related setters

        use them to set several of the common keys of the schema
    """

    def set_context(self, context):
        """
        In case we want to overide the default context
        """
        self.schema["@context"] = context

    def set_preamble(self, preamble="", lang=DEFAULT_LANG):
        self.schema["preamble"] = {lang: preamble}

    def set_citation(self, citation):
        self.schema["citation"] = citation

    def set_image(self, image):
        self.schema["image"] = image

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

    def set_pref_label(self, pref_label, lang=DEFAULT_LANG):
        self.schema["prefLabel"] = {lang: pref_label}

    def set_description(self, description):
        self.schema["description"] = description

    """
        getters

        to access the content of some of the keys of the schema
        or some of the instance properties
    """

    def get_name(self):
        return self.schema_file.replace("_schema", "")

    def get_filename(self):
        return self.schema_file

    def get_basename(self):
        return Path(self.schema_file).stem

    def get_pref_label(self):
        return self.schema["prefLabel"]

    def get_URI(self):
        return self.URI

    """
    UI: setters specific to the user interface keys of the schema

    The ui has its own dictionnary.

    Mostly used by the Protocol and Activity class.

    """

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

    """
    writing, reading, sorting, unsetting

    Editing and appending things to the dictionnary tends to give json output
    that is not standardized: the @context can end up at the bottom for one file
    and stay at the top for another.
    So there are a couple of sorting methods to rearrange the keys of
    the different dictionaries and those are called right before writing the jsonld file.

    Those methods enforces a certain order or keys in the output and
    also remove any empty or unknown keys.
    """

    # TODO allow for unknown keys to be added because otherwise adding new fields in the json always
    # forces you to go and change those `schema_order` and `ui_order` otherwise they will not be added.
    #
    # This will require modifying the helper function `reorder_dict_skip_missing`
    #

    def sort_schema(self, schema_order):
        """
        The ``schema_order`` is specific to each "level" of the reproschema
        (protocol, activity, item) so that each can be reordered in its own way
        """
        reordered_dict = reorder_dict_skip_missing(self.schema, schema_order)
        self.schema = reordered_dict

    def sort_ui(self, ui_order=["shuffle", "order", "addProperties", "allow"]):
        reordered_dict = reorder_dict_skip_missing(self.schema["ui"], ui_order)
        self.schema["ui"] = reordered_dict

    def __write(self, output_dir):
        """
        Reused by the write method of the children classes
        """
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


def reorder_dict_skip_missing(old_dict, key_list):
    """
    reorders dictionary according to ``key_list``
    removing any key with no associated value
    or that is not in the key list
    """
    return OrderedDict((k, old_dict[k]) for k in key_list if k in old_dict)
