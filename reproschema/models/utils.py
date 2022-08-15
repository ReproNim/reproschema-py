from collections import OrderedDict
from typing import Dict
from typing import List
from typing import Optional

from attrs import define
from attrs import field
from attrs.converters import default_if_none
from attrs.validators import instance_of
from attrs.validators import optional


@define(kw_only=True)
class SchemaUtils:

    schema_order: Optional[list] = field(
        factory=(list),
        converter=default_if_none(default=[]),  # type: ignore
        validator=optional(instance_of(list)),
    )
    #: contains the content that is read from or dumped in JSON
    schema: Optional[dict] = field(
        factory=(dict),
        converter=default_if_none(default={}),  # type: ignore
        validator=optional(instance_of(dict)),
    )

    def sort_schema(self) -> None:
        if self.schema is None or self.schema_order is None:
            return
        reordered_dict = reorder_dict_skip_missing(self.schema, self.schema_order)
        self.schema = reordered_dict
        return reordered_dict

    def drop_empty_values_from_schema(self) -> None:
        tmp = dict(self.schema)
        for key in tmp:
            if self.schema[key] in [{}, [], "", None]:
                self.schema.pop(key)

    def update(self) -> None:
        """Updates the schema content based on the attributes."""

        for key in self.schema_order:
            if key.startswith("@"):
                continue
            self.schema[key] = self.__getattribute__(key)


def reorder_dict_skip_missing(old_dict: Dict, key_list: List) -> OrderedDict:
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
