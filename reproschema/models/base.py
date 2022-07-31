import json
from collections import OrderedDict
from pathlib import Path
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

import attrs
from attrs import define
from attrs import field
from attrs.validators import instance_of

from .ui import UI


DEFAULT_LANG = "en"
DEFAULT_VERSION = "1.0.0-rc4"


@define
class SchemaBase:
    """_summary_

    Returns
    -------
    _type_
        _description_

    Raises
    ------
    ValueError
        _description_
    ValueError
        _description_
    ValueError
        _description_
    """

    """
    base class to deal with reproschema schemas

    The content of the schema is stored in the dictionary ``self.schema``

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

    type: str = field(kw_only=True, default="", validator=[instance_of(str)])
    schemaVersion: str = field(
        kw_only=True,
        default=DEFAULT_VERSION,
        converter=attrs.converters.default_if_none(default=DEFAULT_VERSION),  # type: ignore
    )
    version: str = field(kw_only=True, default="0.0.1", validator=[instance_of(str)])
    at_id: str = field(kw_only=True, default="", validator=[instance_of(str)])
    at_context: str = field(kw_only=True, default="", validator=[instance_of(str)])
    prefLabel: dict = field(kw_only=True, default={}, validator=[instance_of(dict)])
    description: str = field(kw_only=True, default="", validator=[instance_of(str)])

    URI = field(default=None)
    lang = field(default=DEFAULT_LANG)
    schema_order: list = field(
        kw_only=True,
        default=None,
        converter=attrs.converters.default_if_none(default=[]),  # type: ignore
    )
    suffix = field(kw_only=True, default="_schema")
    ext = field(kw_only=True, default=".jsonld")

    def __attrs_post_init__(self) -> None:
        self.at_id = self.at_id.replace(" ", "_")
        if self.description == "":
            self.description = self.at_id.replace("_", " ")
        if self.at_context == "":
            self.at_context: str = self.default_context()
        if self.prefLabel == {}:
            self.prefLabel = {self.lang: self.at_id}
        self.schema = {
            "@type": self.type,
            "schemaVersion": self.schemaVersion,
            "version": self.version,
            "prefLabel": {},
            "description": self.description,
        }
        self.ui = UI(self.type)
        self.update()

    def update(self) -> None:
        self.schema["@id"] = self.at_id
        self.schema["@type"] = self.type
        self.schema["schemaVersion"] = self.schemaVersion
        self.schema["version"] = self.version
        self.schema["@context"] = self.at_context
        self.schema["prefLabel"] = self.prefLabel
        self.schema["description"] = self.description
        self.ui.update()
        self.schema["ui"] = self.ui.schema

    # This probably needs some cleaning but is at the moment necessary to pass
    # the context to the ResponseOption class
    def default_context(self) -> str:
        """
        For now we assume that the github repo will be where schema will be read from.
        """
        URL = "https://raw.githubusercontent.com/ReproNim/reproschema/"
        VERSION = self.schemaVersion or DEFAULT_VERSION
        return URL + VERSION + "/contexts/generic"

    def set_defaults(self, name=None) -> None:
        if not name:
            name = self.at_id
        self.set_filename(name)
        "We use the ``name`` of this class instance for schema keys minus some underscore"
        self.set_pref_label(name.replace("_", " "))
        self.set_description(name.replace("_", " "))

    def set_preamble(
        self, preamble: Optional[str] = None, lang: str = DEFAULT_LANG
    ) -> None:
        if not preamble:
            preamble = ""
        self.schema["preamble"] = {lang: preamble}

    def set_citation(self, citation: str) -> None:
        self.schema["citation"] = citation

    def set_image(self, image) -> None:
        self.schema["image"] = image

    def set_filename(self, name: str) -> None:
        name = name.replace(" ", "_")
        self.at_id = f"{name}{self.suffix}{self.ext}"
        self.update()

    def set_pref_label(self, pref_label: str = None, lang: str = DEFAULT_LANG) -> None:
        if not pref_label:
            return
        self.prefLabel[lang] = pref_label
        self.schema["prefLabel"] = self.prefLabel

    def set_description(self, description: str) -> None:
        self.description = description
        self.schema["description"] = self.description
        # self.update()

    """
        getters

        to access the content of some of the keys of the schema
        or some of the instance properties
    """

    def get_basename(self) -> str:
        return Path(self.at_id).stem

    """
    UI: setters specific to the user interface keys of the schema

    The ui has its own dictionary.

    Mostly used by the Protocol and Activity class.

    """

    def set_ui_default(self) -> None:
        self.schema["ui"] = {
            "shuffle": [],
            "order": [],
            "addProperties": [],
            "allow": [],
        }
        self.set_ui_allow()
        self.set_ui_shuffle()
        self.ui.update()

    def set_ui_shuffle(self, shuffle: bool = False) -> None:
        self.ui.shuffle = shuffle
        self.schema["ui"]["shuffle"] = self.ui.shuffle

    def set_ui_allow(
        self,
        auto_advance: bool = True,
        allow_export: bool = True,
        disable_back: bool = False,
    ) -> None:
        self.ui.AutoAdvance(auto_advance)
        self.ui.DisableBack(disable_back)
        self.ui.AllowExport(allow_export)
        self.schema["ui"]["allow"] = self.ui.allow

    def append_to_ui(self, obj, properties: dict) -> None:
        if obj.skippable:
            properties["allow"] = ["reproschema:Skipped"]

        self.ui.order.append(obj.URI)
        self.ui.add_properties.append(properties)
        self.schema["ui"]["order"].append(obj.URI)
        self.schema["ui"]["addProperties"].append(properties)

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

    def sort(self):
        self.sort_schema()
        self.sort_ui()

    def sort_schema(self) -> None:
        reordered_dict = self.reorder_dict_skip_missing(self.schema, self.schema_order)
        self.schema = reordered_dict

    def sort_ui(self) -> None:
        ui_order = self.ui.schema_order
        reordered_dict = self.reorder_dict_skip_missing(self.schema["ui"], ui_order)
        self.schema["ui"] = reordered_dict

    def __write(self, output_dir: Union[str, Path]) -> None:
        """
        Reused by the write method of the children classes
        """
        if isinstance(output_dir, str):
            output_dir = Path(output_dir)
        with open(output_dir.joinpath(self.at_id), "w") as ff:
            json.dump(self.schema, ff, sort_keys=False, indent=4)

    @classmethod
    def from_data(cls, data: dict):
        klass = cls()
        if klass.type is None:
            raise ValueError("SchemaBase cannot be used to instantiate class")
        if klass.type != data["@type"]:
            raise ValueError(f"Mismatch in type {data['@type']} != {klass.type}")
        klass.schema = data
        return klass

    @classmethod
    def from_file(cls, filepath: Union[str, Path]):
        with open(filepath) as fp:
            data = json.load(fp)
        if "@type" not in data:
            raise ValueError("Missing @type key")
        return cls.from_data(data)

    @staticmethod
    def reorder_dict_skip_missing(old_dict: Dict, key_list: List) -> Dict:
        """
        reorders dictionary according to ``key_list``
        removing any key with no associated value
        or that is not in the key list
        """
        return OrderedDict(
            (k, old_dict[k])
            for k in key_list
            if (k in old_dict and old_dict[k] not in ["", [], None])
        )
