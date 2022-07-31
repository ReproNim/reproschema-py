from collections import OrderedDict
from typing import Dict
from typing import List

from attrs import converters
from attrs import define
from attrs import field


@define
class UI:
    type = field(default=[None])
    add_properties: list = field(default=[])
    order: List[str] = field(default=[None])
    allow: list = field(default=[])
    shuffle: bool = field(default=False)
    auto_advance: bool = field(default=True)
    disable_back: bool = field(default=False)
    allow_export: bool = field(default=True)

    schema: dict = field(
        default={
            "shuffle": [],
            "order": [],
            "addProperties": [],
            "allow": [],
        }
    )

    schema_order = field(
        default=["shuffle", "order", "addProperties", "allow"],
        converter=converters.default_if_none(default=[]),  # type: ignore
    )

    def __attrs_post_init__(self) -> None:
        if self.type == "reproschema:Field":
            self.schema_order = ["inputType", "readonlyValue"]
            self.schema = {"inputType": [], "readonlyValue": []}

    def AutoAdvance(self, value: bool = None) -> None:
        if not value:
            return
        self.auto_advance = value
        if self.auto_advance and "reproschema:AutoAdvance" not in self.allow:
            self.allow.append("reproschema:AutoAdvance")
        elif not self.auto_advance and "reproschema:AutoAdvance" in self.allow:
            self.allow.remove("reproschema:AutoAdvance")

    def DisableBack(self, value: bool = None) -> None:
        if not value:
            return
        self.disable_back = value
        if self.disable_back and "reproschema:DisableBack" not in self.allow:
            self.allow.append("reproschema:DisableBack")
        elif not self.disable_back and "reproschema:DisableBack" in self.allow:
            self.allow.remove("reproschema:DisableBack")

    def AllowExport(self, value: bool = None) -> None:
        if not value:
            return
        self.allow_export = value
        if self.allow_export and "reproschema:AllowExport" not in self.allow:
            self.allow.append("reproschema:AllowExport")
        elif not self.allow_export and "reproschema:AllowExport" in self.allow:
            self.allow.remove("reproschema:AllowExport")

    def update(self) -> None:
        self.schema["shuffle"] = self.shuffle
        self.schema["order"] = self.order
        self.schema["addProperties"] = self.add_properties
        self.schema["allow"] = self.allow
        self.schema = self.sort()

    def sort(self) -> Dict:
        reordered_dict = self.reorder_dict_skip_missing(self.schema, self.schema_order)
        self.schema = reordered_dict
        return reordered_dict

    @staticmethod
    def reorder_dict_skip_missing(old_dict: Dict, key_list: List) -> Dict:
        """
        reorders dictionary according to ``key_list``
        removing any key with no associated value
        or that is not in the key list
        """
        return OrderedDict(
            (k, old_dict[k]) for k in key_list if (k in old_dict and old_dict[k])
        )
