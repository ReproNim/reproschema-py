import json
import os
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from attrs import define
from attrs import field
from attrs.converters import default_if_none
from attrs.validators import in_
from attrs.validators import instance_of
from attrs.validators import optional

from .base import DEFAULT_LANG
from .base import DEFAULT_VERSION
from .utils import reorder_dict_skip_missing


@define(kw_only=True)
class Choice:

    name: Optional[Union[str, Dict[str, str]]] = field(
        default=None,
        converter=default_if_none(default=""),
        validator=optional(instance_of((str, dict))),
    )
    value = field(default=None)
    image: Optional[Union[str, Dict[str, str]]] = field(
        default=None, validator=optional(instance_of((str, dict)))
    )

    lang: Optional[str] = field(
        default=None,
        converter=default_if_none(default=DEFAULT_LANG()),  # type: ignore
        validator=optional(instance_of(str)),
    )
    schema_order: Optional[list] = field(
        default=None,
        converter=default_if_none(
            default=[
                "name",
                "value",
                "image",
            ]
        ),  # type: ignore
        validator=optional(instance_of(list)),
    )

    #: contains the content that is read from or dumped in JSON
    schema: Optional[dict] = field(
        factory=(dict),
        converter=default_if_none(default={}),  # type: ignore
        validator=optional(instance_of(dict)),
    )

    def __attrs_post_init__(self) -> None:

        if isinstance(self.name, str):
            self.name = {self.lang: self.name}

        self.update()
        self.sort()
        self.drop_empty_values_from_schema()

    def update(self) -> None:
        """Updates the schema content based on the attributes."""

        for key in self.schema_order:
            self.schema[key] = self.__getattribute__(key)

    def sort(self) -> None:

        reordered_dict = reorder_dict_skip_missing(self.schema, self.schema_order)

        self.schema = reordered_dict

    def drop_empty_values_from_schema(self) -> None:
        tmp = dict(self.schema)
        for key in tmp:
            if self.schema[key] in [{}, [], ""]:
                self.schema.pop(key)
        self.schema = dict(self.schema)


@define(kw_only=True)
class ResponseOption:

    SUPPORTED_VALUE_TYPES = (
        "",
        "xsd:string",
        "xsd:integer",
        "xsd:float",
        "xsd:date",
        "xsd:datetime",
        "xsd:timeRange",
    )

    at_type: Optional[str] = field(
        default=None,
        converter=default_if_none(default="reproschema:ResponseOption"),  # type: ignore
        validator=in_(
            [
                "reproschema:ResponseOption",
            ]
        ),
    )
    at_id: Optional[str] = field(
        default=None,
        converter=default_if_none(default="valueConstraints"),  # type: ignore
        validator=[instance_of(str)],
    )
    schemaVersion: Optional[str] = field(
        default=DEFAULT_VERSION(),
        converter=default_if_none(default=DEFAULT_VERSION()),  # type: ignore
        validator=[instance_of(str)],
    )
    at_context: str = field(
        validator=[instance_of(str)],
    )

    @at_context.default
    def _default_context(self) -> str:
        """
        For now we assume that the github repo will be where schema will be read from.
        """
        URL = "https://raw.githubusercontent.com/ReproNim/reproschema/"
        VERSION = self.schemaVersion or DEFAULT_VERSION()
        return URL + VERSION + "/contexts/generic"

    valueType: str = field(
        factory=(str),
        converter=default_if_none(default=""),  # type: ignore
        validator=optional(in_(SUPPORTED_VALUE_TYPES)),
    )

    choices: Optional[Union[str, List[Choice]]] = field(
        factory=(list),
        converter=default_if_none(default=[]),  # type: ignore
        validator=optional(instance_of((str, list))),
    )

    multipleChoice: bool = field(
        default=None,
        validator=optional(instance_of(bool)),
    )

    minValue: int = field(
        default=None,
        validator=optional(instance_of(int)),
    )

    maxValue: int = field(
        default=None,
        validator=optional(instance_of(int)),
    )

    unitOptions: str = field(
        default=None,
        converter=default_if_none(default=""),  # type: ignore
        validator=optional(instance_of(str)),
    )

    unitCode: str = field(
        default=None,
        converter=default_if_none(default=""),  # type: ignore
        validator=optional(instance_of(str)),
    )

    datumType: str = field(
        default=None,
        converter=default_if_none(default=""),  # type: ignore
        validator=optional(instance_of(str)),
    )

    maxLength: int = field(
        default=None,
        validator=optional(instance_of(int)),
    )

    """
    Non schema based attributes: OPTIONAL

    Those attributes help with file management
    and with printing json files with standardized key orders
    """
    lang: Optional[str] = field(
        default=None,
        converter=default_if_none(default=DEFAULT_LANG()),  # type: ignore
        validator=optional(instance_of(str)),
    )
    schema_order: Optional[list] = field(
        default=None,
        converter=default_if_none(
            default=[
                "@type",
                "@context",
                "@id",
                "valueType",
                "choices",
                "multipleChoice",
                "minValue",
                "maxValue",
                "unitOptions",
                "unitCode",
                "datumType",
                "maxLength",
            ]
        ),  # type: ignore
        validator=optional(instance_of(list)),
    )
    output_dir = field(
        default=None,
        converter=default_if_none(default=Path.cwd()),  # type: ignore
        validator=optional(instance_of((str, Path))),
    )
    suffix: Optional[str] = field(
        default=None,
        converter=default_if_none(default=""),  # type: ignore
        validator=optional(instance_of(str)),
    )
    ext: Optional[str] = field(
        default=None,
        converter=default_if_none(default=".jsonld"),  # type: ignore
        validator=optional(instance_of(str)),
    )
    URI: Optional[Path] = field(
        default=None,
        converter=default_if_none(default=Path("")),  # type: ignore
        validator=optional(instance_of((str, Path))),
    )

    #: contains the content that is read from or dumped in JSON
    schema: Optional[dict] = field(
        factory=(dict),
        converter=default_if_none(default={}),  # type: ignore
        validator=optional(instance_of(dict)),
    )

    def set_defaults(self) -> None:
        self.schema["@type"] = self.at_type
        self.set_filename()

    def set_valueType(self, value: str = None) -> None:
        if value is not None:
            self.valueType = f"xsd:{value}"
        self.update()

    def values_all_options(self):
        return [i["value"] for i in self.choices if "value" in i]

    def set_min(self, value: int = None) -> None:
        if value is not None:
            self.minValue = value
        elif len(self.choices) > 1:
            self.minValue = min(self.values_all_options())

    def set_max(self, value: int = None) -> None:
        if value is not None:
            self.maxValue = value
        elif len(self.choices) > 1:
            self.maxValue = max(self.values_all_options())
        self.update()

    def add_choice(
        self,
        name: Optional[str] = None,
        value: Any = None,
        lang: Optional[str] = None,
    ) -> None:
        if lang is None:
            lang = self.lang
        # TODO replace existing choice if already set
        self.choices.append(Choice(name=name, value=value, lang=lang).schema)
        self.set_max()
        self.set_min()

    def update(self) -> None:
        """Updates the schema content based on the attributes."""

        self.schema["@id"] = self.at_id
        self.schema["@type"] = self.at_type
        self.schema["@context"] = self.at_context

        for key in self.schema_order:
            if key.startswith("@"):
                continue
            self.schema[key] = self.__getattribute__(key)

    def set_filename(self, name: str = None) -> None:
        if name is None:
            name = self.at_id
        if name.endswith(self.ext):
            name = name.replace(self.ext, "")
        if name.endswith(self.suffix):
            name = name.replace(self.suffix, "")

        name = name.replace(" ", "_")

        self.at_id = f"{name}{self.suffix}{self.ext}"
        self.URI = os.path.join(self.output_dir, self.at_id)
        self.update()

    def get_basename(self) -> str:
        return Path(self.at_id).stem

    def sort(self) -> None:
        self.sort_schema()

    def sort_schema(self) -> None:
        reordered_dict = reorder_dict_skip_missing(self.schema, self.schema_order)
        self.schema = reordered_dict

    def drop_empty_values_from_schema(self) -> None:
        tmp = dict(self.schema)
        for key in tmp:
            if self.schema[key] in [{}, [], "", None]:
                self.schema.pop(key)

    def write(self, output_dir: Optional[Union[str, Path]] = None) -> None:

        self.update()
        self.sort()
        self.drop_empty_values_from_schema()

        if output_dir is None:
            output_dir = self.output_dir

        if isinstance(output_dir, str):
            output_dir = Path(output_dir)

        output_dir.mkdir(parents=True, exist_ok=True)

        with open(output_dir.joinpath(self.at_id), "w") as ff:
            json.dump(self.schema, ff, sort_keys=False, indent=4)

    @classmethod
    def from_data(cls, data: dict):
        klass = cls()
        if klass.at_type is None:
            raise ValueError("SchemaBase cannot be used to instantiate class")
        if klass.at_type != data["@type"]:
            raise ValueError(f"Mismatch in type {data['@type']} != {klass.at_type}")
        klass.schema = data
        return klass

    @classmethod
    def from_file(cls, filepath: Union[str, Path]):
        with open(filepath) as fp:
            data = json.load(fp)
        if "@type" not in data:
            raise ValueError("Missing @type key")
        return cls.from_data(data)
