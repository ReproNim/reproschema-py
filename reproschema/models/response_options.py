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

from .base import DEFAULT_VERSION
from .utils import SchemaUtils


@define(kw_only=True)
class unitOption(SchemaUtils):
    """
    An object to represent a human displayable name,
    alongside the more formal value for units.
    """

    #: The value for each option in choices or in additionalNotesObj
    value: Any = field(default=None)
    #: The preferred label.
    prefLabel: Optional[Union[str, Dict[str, str]]] = field(
        factory=(dict),
        converter=default_if_none(default={}),  # type: ignore
        validator=optional(instance_of((dict, str))),
    )

    def __attrs_post_init__(self) -> None:

        if self.schema_order in [None, []]:
            self.schema_order = [
                "prefLabel",
                "value",
            ]
        if isinstance(self.prefLabel, str):
            self.prefLabel = {self.lang: self.prefLabel}

        self.update()
        self.sort_schema()

    def set_pref_label(
        self, pref_label: Optional[str] = None, lang: Optional[str] = None
    ) -> None:
        if pref_label is None:
            return
        if lang is None:
            lang = self.lang

        self.prefLabel[lang] = pref_label
        self.update()


@define(kw_only=True)
class Choice(SchemaUtils):
    """An object to describe a response option."""

    #: The name of the item.
    name: Optional[Union[str, Dict[str, str]]] = field(
        default=None,
        converter=default_if_none(default=""),
        validator=optional(instance_of((str, dict))),
    )
    #: The value for each option in choices or in additionalNotesObj
    value: Any = field(default=None)
    #: An image of the item. This can be a URL or a fully described ImageObject.
    image: Optional[Union[str, Dict[str, str]]] = field(
        default=None, validator=optional(instance_of((str, dict)))
    )

    def __attrs_post_init__(self) -> None:

        if self.schema_order in [None, []]:
            self.schema_order = [
                "name",
                "value",
                "image",
            ]

        if isinstance(self.name, str):
            self.name = {self.lang: self.name}

        self.update()
        self.sort_schema()
        self.drop_empty_values_from_schema()


@define(kw_only=True)
class ResponseOption(SchemaUtils):

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

    #: The type of the response of an item. For example, string, integer, etc.
    valueType: str = field(
        factory=(str),
        converter=default_if_none(default=""),  # type: ignore
        validator=optional(in_(SUPPORTED_VALUE_TYPES)),
    )
    #: List the available options for response of the Field item.
    choices: Optional[Union[str, List[Choice]]] = field(
        factory=(list),
        converter=default_if_none(default=[]),  # type: ignore
        validator=optional(instance_of((str, list))),
    )
    #: Indicates if response for the Field item has one or more answer.
    multipleChoice: Optional[bool] = field(
        default=None,
        validator=optional(instance_of(bool)),
    )
    #: The lower value of some characteristic or property.
    minValue: Optional[int] = field(
        default=None,
        validator=optional(instance_of(int)),
    )
    #: The upper value of some characteristic or property.
    maxValue: Optional[int] = field(
        default=None,
        validator=optional(instance_of(int)),
    )
    #: A list to represent a human displayable name alongside the more formal value for units.
    unitOptions: Optional[list] = field(
        default=None,
        converter=default_if_none(default=[]),  # type: ignore
        validator=optional(instance_of(list)),
    )
    #: The unit of measurement given using the UN/CEFACT Common Code (3 characters) or a URL.
    # Other codes than the UN/CEFACT Common Code may be used with a prefix followed by a colon.
    unitCode: Optional[str] = field(
        default=None,
        converter=default_if_none(default=""),  # type: ignore
        validator=optional(instance_of(str)),
    )
    #: Indicates what type of datum the response is
    # (e.g. range,count,scalar etc.) for the Field item.
    datumType: Optional[str] = field(
        default=None,
        converter=default_if_none(default=""),  # type: ignore
        validator=optional(instance_of(str)),
    )
    # Technically not in the schema, but useful for the UI
    maxLength: Optional[int] = field(
        default=None,
        validator=optional(instance_of(int)),
    )

    """

    Non schema based attributes: OPTIONAL

    Those attributes help with file management
    and with printing json files with standardized key orders

    """

    output_dir: Optional[Union[str, Path]] = field(
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

    def __attrs_post_init__(self) -> None:

        if self.schema_order in [None, []]:
            self.schema_order = [
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

    """
    SETTERS:
    """

    def set_defaults(self) -> None:
        self.schema["@type"] = self.at_type
        self.set_filename()

    def set_valueType(self, value: str = None) -> None:
        """_summary_

        :param value: _description_, defaults to None
        :type value: str, optional
        """
        if value is not None:
            self.valueType = f"xsd:{value}"
        self.update()

    def set_min(self, value: int = None) -> None:
        """_summary_

        :param value: _description_, defaults to None
        :type value: int, optional
        """
        if value is not None:
            self.minValue = value
        elif len(self.choices) > 1:
            self.minValue = 0
            all_values = self.values_all_options()
            if all(isinstance(x, int) for x in all_values):
                self.minValue = min(all_values)

    def set_max(self, value: int = None) -> None:
        """_summary_

        :param value: _description_, defaults to None
        :type value: int, optional
        """
        if value is not None:
            self.maxValue = value

        elif len(self.choices) > 1:
            all_values = self.values_all_options()
            self.maxValue = len(all_values) - 1
            if all(isinstance(x, int) for x in all_values):
                self.maxValue = max(all_values)

        self.update()

    def values_all_options(self) -> List[Any]:
        return [i["value"] for i in self.choices if "value" in i]

    def add_choice(
        self,
        name: Optional[str] = None,
        value: Any = None,
        lang: Optional[str] = None,
    ) -> None:
        """Add a response choice.

        :param name: _description_, defaults to None
        :type name: Optional[str], optional
        :param value: _description_, defaults to None
        :type value: Any, optional
        :param lang: _description_, defaults to None
        :type lang: Optional[str], optional
        """
        if lang is None:
            lang = self.lang
        # TODO replace existing choice if already set
        self.choices.append(Choice(name=name, value=value, lang=lang).schema)
        self.set_max()
        self.set_min()

    """
    MISC
    """

    def update(self) -> None:
        self.schema["@id"] = self.at_id
        self.schema["@type"] = self.at_type
        self.schema["@context"] = self.at_context

        super().update()

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

    def write(self, output_dir: Optional[Union[str, Path]] = None) -> None:

        self.update()
        self.sort_schema()
        self.drop_empty_values_from_schema()

        if output_dir is None:
            output_dir = self.output_dir

        if isinstance(output_dir, str):
            output_dir = Path(output_dir)

        output_dir.mkdir(parents=True, exist_ok=True)

        with open(output_dir.joinpath(self.at_id), "w") as ff:
            json.dump(self.schema, ff, sort_keys=False, indent=4)
