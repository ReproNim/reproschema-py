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
        """Append Field or Activity to the UI schema.

        :param obj: _description_
        :type obj: _type_
        :param variableName: _description_, defaults to None
        :type variableName: Optional[str], optional
        """

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
    """An object to describe the various properties added to assessments and fields."""

    #: The name used to represent an item.
    variableName: Optional[str] = field(
        default=None,
        converter=default_if_none(default=""),  # type: ignore
        validator=optional(instance_of(str)),
    )
    #: A pointer to the node describing the item.
    isAbout: Optional[str] = field(
        default=None,
        converter=default_if_none(default=""),  # type: ignore
        validator=optional(instance_of(str)),
    )
    #: The preferred label.
    prefLabel: Optional[Union[str, Dict[str, str]]] = field(
        default=None,
        converter=default_if_none(default={}),  # type: ignore
        validator=optional(instance_of((str, dict))),
    )
    #: An element to describe (by boolean or conditional statement)
    # visibility conditions of items in an assessment.
    isVis: Optional[Union[str, bool]] = field(
        default=None, validator=optional(instance_of((bool, str)))
    )
    #: Whether the property must be filled in to complete the action.
    requiredValue: Optional[bool] = field(
        default=None,
        validator=optional(instance_of(bool)),
    )
    #: List of items indicating properties allowed.
    allow: Optional[List[str]] = field(
        factory=list,
        converter=default_if_none(default=[]),  # type: ignore
        validator=optional(instance_of(list)),
    )
    #: An element to limit the duration (uses ISO 8601)
    # this activity is allowed to be completed by once activity is available.
    limit: Optional[str] = field(
        default=None,
        converter=default_if_none(default=""),  # type: ignore
        validator=optional(instance_of(str)),
    )
    #: Defines number of times the item is allowed to be redone.
    maxRetakes: Optional[str] = field(
        default=None,
        converter=default_if_none(default=""),  # type: ignore
        validator=optional(instance_of(str)),
    )
    #: Present activity/item within some random offset of activity available time up
    # to the maximum specified by this ISO 8601 duration
    randomMaxDelay: Optional[str] = field(
        default=None,
        converter=default_if_none(default=""),  # type: ignore
        validator=optional(instance_of(str)),
    )
    #: An element to set make activity available/repeat info using ISO 8601 repeating interval format.
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
