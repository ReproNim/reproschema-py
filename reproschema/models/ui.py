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

from .utils import SchemaUtils


@define(
    kw_only=True,
)
class UI(SchemaUtils):

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

    def __attrs_post_init__(self) -> None:

        if self.schema_order in [None, []]:
            self.schema_order = [
                "shuffle",
                "order",
                "addProperties",
                "allow",
                "limit",
                "randomMaxDelay",
                "schedule",
            ]
            if self.at_type == "reproschema:Field":
                self.schema_order = ["inputType", "readonlyValue"]

        if self.at_type == "reproschema:ResponseOption":
            self.AllowExport = False
            self.AutoAdvance = False

        self.update()

    def append(self, obj, variableName: Optional[str] = None) -> None:

        this_property = AdditionalProperty(
            variableName=variableName,
            isAbout=obj.URI,
            prefLabel=obj.prefLabel,
            isVis=obj.visible,
            requiredValue=obj.required,
            skippable=obj.skippable,
            limit=obj.limit,
            randomMaxDelay=obj.randomMaxDelay,
            schedule=obj.schedule,
        )
        this_property.update()
        this_property.sort_schema()
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

        self.sort_schema()


@define(
    kw_only=True,
)
class AdditionalProperty(SchemaUtils):

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

    skippable: Optional[bool] = field(
        factory=(bool),
        converter=default_if_none(default=True),  # type: ignore
        validator=optional(instance_of(bool)),
    )

    def __attrs_post_init__(self) -> None:

        if self.schema_order in [None, []]:
            self.schema_order = [
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

    def update(self) -> None:
        if self.skippable is True:
            self.allow = ["reproschema:Skipped"]
        super().update()
