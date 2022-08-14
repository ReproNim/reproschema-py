from pathlib import Path
from typing import Optional

from .base import DEFAULT_LANG
from .base import SchemaBase


class ResponseOption(SchemaBase):
    """
    class to deal with reproschema response options
    """

    def __init__(
        self,
        name="valueConstraints",
        multiple_choice=None,
        schemaVersion=None,
        output_dir=Path.cwd(),
    ):

        options_order = [
            "@context",
            "@type",
            "@id",
            "valueType",
            "minValue",
            "maxValue",
            "multipleChoice",
            "choices",
        ]

        super().__init__(
            at_id=name,
            at_type="reproschema:ResponseOption",
            schema_order=options_order,
            schemaVersion=schemaVersion,
            ext=".jsonld",
            suffix="",
            output_dir=output_dir,
        )

        self.schema = {"choices": []}
        self.set_multiple_choice(multiple_choice)

    def set_defaults(self) -> None:
        self.schema["@type"] = self.at_type
        self.set_filename()

    def unset(self, keys) -> None:
        if type(keys) == str:
            keys = [keys]
        for i in keys:
            self.schema.pop(i, None)

    def set_type(self, value: str = None) -> None:
        if value is not None:
            self.schema["valueType"] = f"xsd:{value}"

    def values_all_options(self):
        return [i["value"] for i in self.schema["choices"] if "value" in i]

    def set_min(self, value: int = None) -> None:
        if value is not None:
            self.schema["minValue"] = value
        elif len(self.schema["choices"]) > 1:
            self.schema["minValue"] = min(self.values_all_options())

    def set_max(self, value: int = None) -> None:
        if value is not None:
            self.schema["maxValue"] = value
        elif len(self.schema["choices"]) > 1:
            self.schema["maxValue"] = max(self.values_all_options())

    def set_length(self, value: int = None) -> None:
        if value is not None:
            self.schema["maxLength"] = value

        # TODO

    def set_multiple_choice(self, value: bool = None) -> None:
        if value is not None:
            self.multiple_choice = value
            self.schema["multipleChoice"] = value

    def use_preset(self, URI) -> None:
        """
        In case the list response options are read from another file
        like for languages, country, state...
        """
        self.schema["choices"] = URI

    def add_choice(self, choice, value, lang: Optional[str] = None) -> None:
        if lang is None:
            lang = DEFAULT_LANG()
        # TODO replace existing choice if already set
        self.schema["choices"].append({"name": {lang: choice}, "value": value})
        self.set_max()
        self.set_min()
