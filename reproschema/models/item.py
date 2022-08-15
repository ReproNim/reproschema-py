from pathlib import Path
from typing import Dict
from typing import Optional
from typing import Union

from .base import COMMON_SCHEMA_ORDER
from .base import DEFAULT_LANG
from .base import SchemaBase
from .response_options import ResponseOption


class Item(SchemaBase):
    """
    class to deal with reproschema items
    """

    def __init__(
        self,
        name: Optional[str] = "item",
        input_type: Optional[str] = "text",
        question: Optional[Union[dict, str]] = "",
        schemaVersion: Optional[str] = None,
        prefLabel: Optional[str] = "item",
        altLabel: Optional[Dict[str, str]] = None,
        description: Optional[str] = "",
        image: Optional[Union[str, Dict[str, str]]] = None,
        preamble: Optional[str] = None,
        visible: Optional[bool] = True,
        required: Optional[bool] = False,
        skippable: Optional[bool] = True,
        read_only: Optional[bool] = None,
        suffix: Optional[str] = "",
        ext: Optional[str] = ".jsonld",
        output_dir=Path.cwd(),
        lang: Optional[str] = DEFAULT_LANG(),
    ):

        schema_order = COMMON_SCHEMA_ORDER() + [
            "question",
            "responseOptions",
        ]

        super().__init__(
            at_id=name,
            at_type="reproschema:Field",
            inputType=input_type,
            schemaVersion=schemaVersion,
            prefLabel={lang: prefLabel},
            altLabel=altLabel,
            description=description,
            preamble=preamble,
            image=image,
            schema_order=schema_order,
            visible=visible,
            required=required,
            skippable=skippable,
            readonlyValue=read_only,
            suffix=suffix,
            ext=ext,
            output_dir=output_dir,
            lang=lang,
        )

        self.set_question(question=question)

        self.response_options: ResponseOption = ResponseOption()
        self.set_response_options()

        self.set_input_type()

        self.update()

    def set_question(
        self, question: Optional[Union[str, dict]] = None, lang: Optional[str] = None
    ) -> None:

        if question is None:
            question = self.question

        if lang is None:
            lang = self.lang

        if question == {}:
            return

        if isinstance(question, str):
            self.question[lang] = question
        elif isinstance(question, dict):
            self.question = question

        self.update()

    """
    CREATE DIFFERENT ITEMS
    """
    # TODO: items not yet covered
    # audioCheck: AudioCheck/AudioCheck.vue
    # audioRecord: WebAudioRecord/Audio.vue
    # audioPassageRecord: WebAudioRecord/Audio.vue
    # audioImageRecord: WebAudioRecord/Audio.vue
    # audioRecordNumberTask: WebAudioRecord/Audio.vue
    # audioAutoRecord: AudioCheckRecord/AudioCheckRecord.vue
    # documentUpload: DocumentUpload/DocumentUpload.vue
    # save: SaveData/SaveData.vue
    # static: Static/Static.vue
    # StaticReadOnly: Static/Static.vue

    def set_input_type(self) -> None:

        SUPPORTED_TYPES = (
            "text",
            "multitext",
            "integer",
            "float",
            "date",
            "year",
            "timeRange",
            "selectLanguage",
            "selectCountry",
            "selectState",
            "email",
            "pid",
            "select",
            "radio",
            "slider",
        )

        if self.inputType not in SUPPORTED_TYPES:
            raise ValueError(
                f"""
            Input_type {self.inputType} not supported.
            Supported input_types are: {SUPPORTED_TYPES}
            """
            )

        self.ui.inputType = self.inputType if self.inputType != "integer" else "number"

        if not self.inputType or self.inputType in [
            "text",
            "multitext",
            "selectLanguage",
            "email",
            "pid",
            "selectLanguage",
            "selectCountry",
            "selectState",
        ]:
            self.response_options.set_valueType("string")

        if not self.inputType or self.inputType in ["select", "radio", "slider"]:
            return

        if self.inputType in ["text", "multitext"]:
            self.response_options.maxLength = 300
            self.response_options.update()

        elif self.inputType in ["integer", "float", "date"]:
            self.response_options.set_valueType(self.inputType)

        elif self.inputType == "year":
            self.response_options.set_valueType("date")

        elif self.inputType == "timeRange":
            self.response_options.set_valueType("datetime")

        elif self.inputType == "selectLanguage":
            URL = "https://raw.githubusercontent.com/ReproNim/reproschema-library/"
            self.response_options.multipleChoice = True
            self.response_options.choices = f"{URL}master/resources/languages.json"

        elif self.inputType == "selectCountry":
            URL = "https://raw.githubusercontent.com/samayo/country-json/master/src/country-by-name.json"
            self.response_options.maxLength = 50
            self.response_options.choices = URL

        elif self.inputType == "selectState":
            URL = "https://gist.githubusercontent.com/mshafrir/2646763/raw/8b0dbb93521f5d6889502305335104218454c2bf/states_hash.json"
            self.response_options.choices = URL

    """
    input types with 'different response choices'

    Those methods require an instance of ResponseOptions as input and
    it will replace the one initialized in the construction.
    """

    def set_input_type_as_radio(self, response_options: ResponseOption) -> None:
        self.set_input_type_rasesli("radio", response_options)

    def set_input_type_as_select(self, response_options: ResponseOption) -> None:
        self.set_input_type_rasesli("select", response_options)

    def set_input_type_as_slider(self, response_options: ResponseOption) -> None:
        response_options.multipleChoice = False
        self.set_input_type_rasesli("slider", response_options)

    def set_input_type_rasesli(
        self, arg0: str, response_options: ResponseOption
    ) -> None:
        self.ui.inputType = arg0
        response_options.set_valueType("integer")
        self.response_options = response_options

    """
    writing, reading, sorting, unsetting
    """

    def set_response_options(self) -> None:
        """
        Passes the content of the response options to the schema of the item.
        To be done before writing the item
        """
        self.response_options.update()
        self.response_options.sort()
        self.response_options.drop_empty_values_from_schema()
        self.response_options.schema.pop("@id")
        self.response_options.schema.pop("@type")
        self.response_options.schema.pop("@context")
        self.schema["responseOptions"] = self.response_options.schema

    def unset(self, keys) -> None:
        """
        Mostly used to remove some empty keys from the schema. Rarely used.
        """
        for i in keys:
            self.schema.pop(i, None)

    def write(self, output_dir=None) -> None:
        if output_dir is None:
            output_dir = self.output_dir
        self.set_response_options()
        super().write(output_dir)
