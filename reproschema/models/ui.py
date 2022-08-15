import re
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

from .utils import reorder_dict_skip_missing

# from .protocol import Protocol
# from .activity import Activity


@define(
    kw_only=True,
)
class UI:

    #: this is more to help set up things on the UI side than purely schema related
    SUPPORTED_INPUT_TYPES = (
        "text",
        "multitext",
        "number",
        "float",
        "date",
        "time",
        "timeRange",
        "year",
        "selectLanguage",
        "selectCountry",
        "selectState",
        "email",
        "pid",
        "select",
        "radio",
        "slider",
    )

    at_type: str = field(
        factory=str,
        validator=in_(
            [
                "reproschema:Protocol",
                "reproschema:Activity",
                "reproschema:Field",
                "reproschema:ResponseOption",
            ]
        ),
    )

    shuffle: Optional[bool] = field(
        default=None,
        validator=optional(instance_of(bool)),
    )

    addProperties: Optional[List[Dict[str, Any]]] = field(
        factory=(list),
        validator=optional(instance_of(list)),
    )

    order: List[str] = field(
        factory=(list),
        validator=optional(instance_of(list)),
    )

    AutoAdvance: Optional[bool] = field(
        default=None,
        converter=default_if_none(default=True),  # type: ignore
        validator=optional(instance_of(bool)),
    )

    DisableBack: Optional[bool] = field(
        default=None,
        converter=default_if_none(default=False),  # type: ignore
        validator=optional(instance_of(bool)),
    )

    AllowExport: Optional[bool] = field(
        default=None,
        converter=default_if_none(default=True),  # type: ignore
        validator=optional(instance_of(bool)),
    )

    readonlyValue: Optional[bool] = field(
        default=None,
        validator=optional(instance_of(bool)),
    )

    inputType: Optional[str] = field(
        default=None, validator=optional(in_(SUPPORTED_INPUT_TYPES))
    )

    allow: Optional[List[str]] = field(
        default=None,
        converter=default_if_none(default=[]),  # type: ignore
        validator=optional(instance_of(list)),
    )

    schema_order: Optional[List[str]] = field(
        validator=optional(instance_of(list)),
    )

    @schema_order.default
    def _default_schema_order(self) -> list:
        default = ["shuffle", "order", "addProperties", "allow"]
        if self.at_type == "reproschema:Field":
            default = ["inputType", "readonlyValue"]
        return default

    schema: Optional[Dict[str, Any]] = field(
        validator=optional(instance_of(dict)),
    )

    @schema.default
    def _default_schema(self) -> dict:
        default = {
            "shuffle": [],
            "order": [],
            "addProperties": [],
            "allow": [],
        }
        if self.at_type == "reproschema:Field":
            default = {"inputType": [], "readonlyValue": []}
        return default

    def __attrs_post_init__(self) -> None:

        if self.at_type == "reproschema:ResponseOption":
            self.AllowExport = False
            self.AutoAdvance = False

        self.update()

    def append(self, obj, variableName: Optional[str] = None) -> None:

        this_property = AddtionalPropertity(
            variableName=variableName,
            isAbout=obj.URI,
            prefLabel=obj.prefLabel,
            isVis=obj.visible,
            requiredValue=obj.required,
            skippable=obj.skippable,
        )
        this_property.update()
        this_property.sort()
        this_property.drop_empty_values_from_schema()

        self.order.append(obj.URI)
        self.addProperties.append(this_property.schema)
        self.update()

    def update(self) -> None:

        for attrib in ["DisableBack", "AutoAdvance", "AllowExport"]:
            if (
                self.__getattribute__(attrib)
                and f"reproschema:{attrib}" not in self.allow
            ):
                self.allow.append(f"reproschema:{attrib}")
            elif (
                not self.__getattribute__(attrib)
                and f"reproschema:{attrib}" in self.allow
            ):
                self.allow.remove(f"reproschema:{attrib}")

        if self.readonlyValue is not None:
            self.schema["readonlyValue"] = self.readonlyValue

        self.schema["shuffle"] = self.shuffle
        self.schema["order"] = self.order
        self.schema["addProperties"] = self.addProperties
        self.schema["allow"] = self.allow

        self.schema["inputType"] = self.inputType

        self.sort()

    def sort(self) -> Dict[str, Any]:
        if self.schema is None:
            return
        reordered_dict = reorder_dict_skip_missing(self.schema, self.schema_order)
        self.schema = reordered_dict
        return reordered_dict


@define(
    kw_only=True,
)
class AddtionalPropertity:

    variableName: Optional[str] = field(
        default=None,
        converter=default_if_none(default=""),  # type: ignore
        validator=optional(instance_of(str)),
    )
    isAbout: Optional[str] = field(
        default=None,
        converter=default_if_none(default=""),  # type: ignore
        validator=optional(instance_of(str)),
    )
    prefLabel: Optional[Union[str, Dict[str, str]]] = field(
        default=None,
        converter=default_if_none(default={}),  # type: ignore
        validator=optional(instance_of((str, dict))),
    )
    isVis: Optional[bool] = field(
        default=None,
        validator=optional(instance_of(bool)),
    )
    requiredValue: Optional[bool] = field(
        default=None,
        validator=optional(instance_of(bool)),
    )
    allow: Optional[List[str]] = field(
        factory=list,
        converter=default_if_none(default=[]),  # type: ignore
        validator=optional(instance_of(list)),
    )
    limit: Optional[str] = field(
        default=None,
        converter=default_if_none(default=""),  # type: ignore
        validator=optional(instance_of(str)),
    )
    maxRetakes: Optional[str] = field(
        default=None,
        converter=default_if_none(default=""),  # type: ignore
        validator=optional(instance_of(str)),
    )
    randomMaxDelay: Optional[str] = field(
        default=None,
        converter=default_if_none(default=""),  # type: ignore
        validator=optional(instance_of(str)),
    )
    schedule: Optional[str] = field(
        default=None,
        converter=default_if_none(default=""),  # type: ignore
        validator=optional(instance_of(str)),
    )

    schema_order: Optional[List[str]] = field(
        default=None,
        converter=default_if_none(
            default=[
                "variableName",
                "isAbout",
                "prefLabel",
                "isVis",
                "requiredValue",
                "allow",
                "limit",
                "maxRetakes",
                "randomMaxDelay",
                "schedule",
            ]
        ),  # type: ignore
        validator=optional(instance_of(list)),
    )

    skippable: Optional[bool] = field(
        factory=(bool),
        converter=default_if_none(default=True),  # type: ignore
        validator=optional(instance_of(bool)),
    )

    schema: Optional[Dict[str, Any]] = field(
        factory=(dict),
        validator=optional(instance_of(dict)),
    )

    def update(self) -> None:
        """Updates the schema content based on the attributes."""
        if self.skippable is True:
            self.allow = ["reproschema:Skipped"]
        for key in self.schema_order:
            self.schema[key] = self.__getattribute__(key)

    def drop_empty_values_from_schema(self) -> None:
        tmp = dict(self.schema)
        for key in tmp:
            if self.schema[key] in [{}, [], "", None]:
                self.schema.pop(key)

    def sort(self) -> Dict[str, Any]:
        if self.schema is None:
            return
        reordered_dict = reorder_dict_skip_missing(self.schema, self.schema_order)
        self.schema = reordered_dict
        return reordered_dict
