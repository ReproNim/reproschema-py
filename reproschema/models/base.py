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

from .ui import UI
from .utils import SchemaUtils


def DEFAULT_VERSION() -> str:
    return "1.0.0-rc4"


def COMMON_SCHEMA_ORDER() -> list:
    return [
        "@context",
        "@type",
        "@id",
        "schemaVersion",
        "version",
        "prefLabel",
        "altLabel",
        "description",
        "preamble",
        "image",
        "audio",
        "video",
        "ui",
    ]


@define(kw_only=True)
class AdditionalNoteObj(SchemaUtils):
    """A set of objects to define notes in a field.

    For example, most Redcap and NDA data dictionaries have notes
    for each item which needs to be captured in reproschema.
    """

    #: An element to define the column name where the note was taken from
    column: Optional[str] = field(
        factory=(str),
        converter=default_if_none(default=""),  # type: ignore
        validator=optional(instance_of(str)),
    )
    #: An element to define the source (eg. RedCap, NDA) where the note was taken from.
    source: Optional[str] = field(
        factory=(str),
        converter=default_if_none(default=""),  # type: ignore
        validator=optional(instance_of(str)),
    )
    #: The value for each option in choices or in additionalNotesObj
    value: Any = field(default=None)

    def __attrs_post_init__(self) -> None:

        if self.schema_order in [None, []]:
            self.schema_order = [
                "column",
                "source",
                "value",
            ]

        self.update().sort_schema()


@define(kw_only=True)
class Message(SchemaUtils):
    """An object to define messages in an activity or protocol."""

    #: A JavaScript expression to compute a score from other variables.
    jsExpression: Optional[str] = field(
        factory=(str),
        converter=default_if_none(default=""),  # type: ignore
        validator=optional(instance_of(str)),
    )
    #: The message to be conditionally displayed for an item.
    message: Optional[str] = field(
        factory=(str),
        converter=default_if_none(default=""),  # type: ignore
        validator=optional(instance_of(str)),
    )

    def __attrs_post_init__(self) -> None:

        if self.schema_order in [None, []]:
            self.schema_order = [
                "message",
                "jsExpression",
            ]

        self.update().sort_schema()


@define(kw_only=True)
class SchemaBase(SchemaUtils):
    """
    Schema based attributes: REQUIRED
    """

    at_type: Optional[str] = field(
        factory=(str),
        converter=default_if_none(default="reproschema:Field"),  # type: ignore
        validator=in_(
            [
                "reproschema:Protocol",
                "reproschema:Activity",
                "reproschema:Field",
                "reproschema:ResponseOption",
            ]
        ),
    )
    at_id: Optional[str] = field(
        factory=(str),
        converter=default_if_none(default=""),  # type: ignore
        validator=[instance_of(str)],
    )
    schemaVersion: Optional[str] = field(
        default=DEFAULT_VERSION(),
        converter=default_if_none(default=DEFAULT_VERSION()),  # type: ignore
        validator=[instance_of(str)],
    )
    version: Optional[str] = field(
        default=None,
        converter=default_if_none(default="0.0.1"),  # type: ignore
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

    """
    Schema based attributes: OPTIONAL

    Can be found in the UI class
    - order
    - addProperties
    - allow
    - about
    """

    """
    Protocol, Activity, Field
    """
    # associatedMedia
    prefLabel: Optional[Union[str, Dict[str, str]]] = field(
        factory=(dict),
        converter=default_if_none(default={}),  # type: ignore
        validator=optional(instance_of((str, dict))),
    )
    altLabel: Optional[Union[str, Dict[str, str]]] = field(
        factory=(dict),
        converter=default_if_none(default={}),  # type: ignore
        validator=optional(instance_of((str, dict))),
    )
    # TODO description is language specific?
    description: str = field(
        factory=(str),
        converter=default_if_none(default=""),  # type: ignore
        validator=optional(instance_of(str)),
    )
    image: Optional[Union[str, Dict[str, str]]] = field(
        default=None,
        validator=optional(instance_of((str, dict))),
    )
    audio: Optional[Union[str, Dict[str, str]]] = field(
        default=None,
        validator=optional(instance_of((str, dict))),
    )
    video: Optional[Union[str, Dict[str, str]]] = field(
        default=None,
        validator=optional(instance_of((str, dict))),
    )
    preamble: Optional[dict] = field(
        factory=(dict),
        converter=default_if_none(default={}),  # type: ignore
        validator=optional(instance_of(dict)),
    )

    # Protocol only
    # TODO landing_page is a dict or a list of dict?
    landingPage: Optional[dict] = field(
        factory=(dict),
        converter=default_if_none(default={}),  # type: ignore
        validator=optional(instance_of(dict)),
    )

    """
    Protocol and Activity
    """
    # TODO cronTable
    citation: Optional[str] = field(
        factory=(str),
        converter=default_if_none(default=""),  # type: ignore
        validator=optional(instance_of(str)),
    )
    compute: Optional[List[Dict[str, str]]] = field(
        factory=(list),
        converter=default_if_none(default=[]),  # type: ignore
        validator=optional(instance_of(list)),
    )
    messages: Optional[list] = field(
        factory=(list),
        converter=default_if_none(default=[]),  # type: ignore
        validator=optional(instance_of(list)),
    )

    """
    Activity only
    """
    # TODO overrideProperties

    """
    Field only
    """
    inputType: Optional[str] = field(
        factory=(str),
        converter=default_if_none(default=""),  # type: ignore
        validator=optional(instance_of(str)),
    )
    readonlyValue: Optional[bool] = field(
        factory=(bool),
        validator=optional(instance_of(bool)),
    )
    question: Optional[dict] = field(
        factory=(dict),
        converter=default_if_none(default={}),  # type: ignore
        validator=optional(instance_of(dict)),
    )
    additionalNotesObj: Optional[list] = field(
        factory=(list),
        converter=default_if_none(default=[]),  # type: ignore
        validator=optional(instance_of(list)),
    )

    """
    UI related
    """
    ui: UI = field(
        default=UI(at_type="reproschema:Field"),
        validator=optional(instance_of(UI)),
    )
    visible: bool | str | None = field(
        factory=(bool),
        converter=default_if_none(default=True),  # type: ignore
        validator=optional(instance_of((bool, str))),
    )
    required: Optional[bool] = field(
        factory=(bool),
        validator=optional(instance_of(bool)),
    )
    skippable: Optional[bool] = field(
        factory=(bool),
        converter=default_if_none(default=True),  # type: ignore
        validator=optional(instance_of(bool)),
    )
    limit: Optional[str] = field(
        factory=(str),
        converter=default_if_none(default=""),  # type: ignore
        validator=optional(instance_of(str)),
    )
    randomMaxDelay: Optional[str] = field(
        factory=(str),
        converter=default_if_none(default=""),  # type: ignore
        validator=optional(instance_of(str)),
    )
    schedule: Optional[str] = field(
        factory=(str),
        converter=default_if_none(default=""),  # type: ignore
        validator=optional(instance_of(str)),
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
        factory=(str),
        converter=default_if_none(default="_schema"),  # type: ignore
        validator=optional(instance_of(str)),
    )
    ext: Optional[str] = field(
        factory=(str),
        converter=default_if_none(default=".jsonld"),  # type: ignore
        validator=optional(instance_of(str)),
    )
    URI: Optional[Path] = field(
        default=None,
        converter=default_if_none(default=Path("")),  # type: ignore
        validator=optional(instance_of((str, Path))),
    )

    def set_defaults(self):

        self.ui = UI(at_type=self.at_type, readonlyValue=self.readonlyValue)

        if self.description == "":
            self.description = self.at_id.replace("_", " ")

        if self.prefLabel == "":
            self.prefLabel = self.at_id.replace("_", " ")

        if isinstance(self.prefLabel, str):
            self.prefLabel = {self.lang: self.prefLabel}

        self.set_pref_label()

        self.set_filename()

    def update(self) -> None:
        """Updates the schema content based on the attributes."""
        self.schema["@id"] = self.at_id
        self.schema["@type"] = self.at_type
        self.schema["@context"] = self.at_context
        keys_to_update = [
            "schemaVersion",
            "version",
            "prefLabel",
            "altLabel",
            "description",
            "citation",
            "image",
            "audio",
            "video",
            "preamble",
            "landingPage",
            "compute",
            "question",
            "messages",
            "additionalNotesObj",
        ]
        for key in keys_to_update:
            self.schema[key] = self.__getattribute__(key)

        self.update_ui()

    def update_ui(self) -> None:
        self.ui.update()
        self.schema["ui"] = self.ui.schema

    """SETTERS

    These are "complex" setters to help set fields that are dictionaries,
    or that use other attributes
    or set several attributes at once

    """

    def set_preamble(
        self, preamble: Optional[str] = None, lang: Optional[str] = None
    ) -> None:
        if preamble is None:
            return
        if lang is None:
            lang = self.lang
        if not self.preamble:
            self.preamble = {}
        self.preamble[lang] = preamble
        self.update()

    # TODO move to protocol class?
    def set_landing_page(self, page: Optional[str] = None, lang: Optional[str] = None):
        if page is None:
            return
        if lang is None:
            lang = self.lang
        self.landingPage = {"@id": page, "inLanguage": lang}
        self.update()

    def set_compute(self, variable, expression):
        self.compute = [{"variableName": variable, "jsExpression": expression}]
        self.update()

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

    def set_alt_label(
        self, alt_label: Optional[str] = None, lang: Optional[str] = None
    ) -> None:
        if alt_label is None:
            return
        if lang is None:
            lang = self.lang
        self.alt_label[lang] = alt_label
        self.update()

    def set_pref_label(
        self, pref_label: Optional[str] = None, lang: Optional[str] = None
    ) -> None:
        if lang is None:
            lang = self.lang

        if pref_label is None:
            if isinstance(self.prefLabel, dict) and (
                self.prefLabel == {}
                or self.prefLabel[lang]
                in [
                    "protocol",
                    "activity",
                    "item",
                ]
            ):
                self.set_pref_label(pref_label=self.at_id.replace("_", " "), lang=lang)
                # pref_label = self.at_id.replace("_", " ")
            return

        self.prefLabel[lang] = pref_label
        self.update()

    """GETTERS
    """

    def get_basename(self) -> str:
        return Path(self.at_id).stem

    """
    writing, reading, sorting, unsetting

    Editing and appending things to the dictionary tends to give json output
    that is not standardized.
    For example: the `@context` can end up at the bottom for one file
    and stay at the top for another.
    So there are a couple of sorting methods to rearrange the keys of
    the different dictionaries and those are called right before writing the output file.

    Those methods enforces a certain order or keys in the output and
    also remove any empty or unknown keys.
    """

    def sort(self) -> None:
        self.sort_schema()
        self.update_ui()

    def write(self, output_dir: Optional[Union[str, Path]] = None) -> None:

        self.sort()

        self.drop_empty_values_from_schema()

        if output_dir is None:
            output_dir = self.output_dir

        if isinstance(output_dir, str):
            output_dir = Path(output_dir)

        output_dir.mkdir(parents=True, exist_ok=True)

        with open(output_dir.joinpath(self.at_id), "w") as ff:
            json.dump(self.schema, ff, sort_keys=False, indent=4)
