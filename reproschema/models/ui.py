from collections import OrderedDict
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from attrs import define
from attrs import field
from attrs.converters import default_if_none
from attrs.validators import in_
from attrs.validators import instance_of
from attrs.validators import optional


@define(
    kw_only=True,
)
class UI:

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

    def append(self, obj=None, variableName: Optional[str] = None) -> None:
        obj_properties = {
            "variableName": variableName,
            "isAbout": obj.URI,
            "prefLabel": obj.prefLabel,
            "isVis": obj.visible,
        }
        if obj.required is not None:
            obj_properties["requiredValue"] = obj.required

        if obj.skippable is True:
            obj_properties["allow"] = ["reproschema:Skipped"]

        self.order.append(obj.URI)
        self.addProperties.append(obj_properties)
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
        reordered_dict = self.reorder_dict_skip_missing(self.schema, self.schema_order)
        self.schema = reordered_dict
        return reordered_dict

    @staticmethod
    def reorder_dict_skip_missing(
        old_dict: Dict[Any, Any], key_list: List[Any]
    ) -> Dict:
        """
        reorders dictionary according to ``key_list``
        removing any key with no associated value
        or that is not in the key list
        """
        return OrderedDict(
            (k, old_dict[k])
            for k in key_list
            if (k in old_dict and old_dict[k] not in [[], "", None])
        )
