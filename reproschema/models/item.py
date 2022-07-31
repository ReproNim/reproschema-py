from .base import SchemaBase
from .response_options import ResponseOption

DEFAULT_LANG = "en"

schema_order = [
    "@context",
    "@type",
    "@id",
    "prefLabel",
    "description",
    "schemaVersion",
    "version",
    "ui",
    "question",
    "responseOptions",
]


class Item(SchemaBase):
    """
    class to deal with reproschema items
    """

    def __init__(
        self,
        name: str = "item",
        input_type: str = "text",
        question: str = "",
        schemaVersion=None,
        suffix="",
        ext=".jsonld",
        visible: bool = True,
        required: bool = False,
        skippable: bool = True,
    ):
        super().__init__(
            at_id=name,
            schemaVersion=schemaVersion,
            type="reproschema:Field",
            schema_order=schema_order,
            suffix=suffix,
            ext=ext,
        )
        self.schema["ui"] = self.ui.schema
        self.schema["question"] = {self.lang: question}
        self.input_type = input_type
        self.visible = visible
        self.required = required
        self.skippable = skippable
        self.question = question

        """
        The responseOptions dictionary is kept empty until the file has to be written
        then it gets its content wit the method `set_response_options`
        from the `options` dictionary of an instance of the ResponseOptions class
        that is kept in ``self.response_options``
        """
        self.response_options: ResponseOption = ResponseOption()
        self.set_response_options()

        super().set_defaults(self.at_id)
        self.set_input_type()

    def set_question(self, question, lang=DEFAULT_LANG):
        # TODO add test to check adding several questions to an item
        self.schema["question"][lang] = question

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

    def set_input_type(self):
        if not self.input_type:
            return
        if self.input_type == "text":
            self.set_input_type_as_text()
        if self.input_type == "multitext":
            self.set_input_type_as_multitext()
        elif self.input_type == "int":
            self.set_input_type_numeric("number", "integer")
        elif self.input_type == "float":
            self.set_input_type_numeric("float", "float")
        elif self.input_type == "year":
            self.schema["ui"]["inputType"] = "year"
            self.response_options.set_type("date")
            self.response_options.unset(
                ["maxLength", "choices", "maxValue", "multipleChoice", "minValue"]
            )
        elif self.input_type == "date":
            self.schema["ui"]["inputType"] = "date"
            self.response_options.set_type("date")
            self.response_options.unset(
                ["maxLength", "choices", "maxValue", "multipleChoice", "minValue"]
            )
        elif self.input_type == "time_range":
            self.schema["ui"]["inputType"] = "timeRange"
            self.response_options.set_type("datetime")
            self.response_options.unset(
                ["maxLength", "choices", "maxValue", "multipleChoice", "minValue"]
            )
        elif self.input_type == "language":
            self.set_input_type_as_language()
        elif self.input_type == "country":
            self.set_input_type_as_country()
        elif self.input_type == "state":
            self.set_input_type_as_state()
        elif self.input_type == "email":
            self.schema["ui"]["inputType"] = "email"
            self.response_options.set_type("string")
            self.response_options.unset(
                ["maxLength", "choices", "maxValue", "multipleChoice", "minValue"]
            )
        elif self.input_type == "id":
            self.schema["ui"]["inputType"] = "pid"
            self.response_options.set_type("string")
            self.response_options.unset(
                ["maxLength", "choices", "maxValue", "multipleChoice", "minValue"]
            )

    def set_input_type_numeric(self, arg0, arg1):
        self.schema["ui"]["inputType"] = arg0
        self.response_options.set_type(arg1)
        self.response_options.unset(
            ["maxLength", "choices", "maxValue", "multipleChoice", "minValue"]
        )

    """
    input types with preset response choices
    """

    def set_input_type_as_language(self):

        URL = self.set_input_from_preset(
            "https://raw.githubusercontent.com/ReproNim/reproschema-library/",
            "selectLanguage",
        )

        self.response_options.set_multiple_choice(True)
        self.response_options.use_preset(f"{URL}master/resources/languages.json")

    def set_input_type_as_country(self):

        URL = self.set_input_from_preset(
            "https://raw.githubusercontent.com/samayo/country-json/master/src/country-by-name.json",
            "selectCountry",
        )

        self.response_options.use_preset(URL)
        self.response_options.set_length(50)

    def set_input_type_as_state(self):

        URL = self.set_input_from_preset(
            "https://gist.githubusercontent.com/mshafrir/2646763/raw/8b0dbb93521f5d6889502305335104218454c2bf/states_hash.json",
            "selectState",
        )

        self.response_options.use_preset(URL)

    def set_input_from_preset(self, arg0, arg1):
        result = arg0
        self.schema["ui"]["inputType"] = arg1
        self.response_options.set_type("string")
        self.response_options.unset(
            ["maxLength", "choices", "maxValue", "multipleChoice", "minValue"]
        )
        return result

    """
    input types requiring user typed input
    """

    def set_input_type_as_text(self, length=300):
        self.set_input_type_generic_text("text", length)
        self.response_options.unset(
            ["maxValue", "minValue", "multipleChoice", "choices"]
        )

    def set_input_type_as_multitext(self, length=300):
        self.set_input_type_generic_text("multitext", length)
        self.response_options.unset(
            ["maxValue", "minValue", "multipleChoice", "choices"]
        )

    def set_input_type_generic_text(self, arg0, length):
        self.schema["ui"]["inputType"] = arg0
        self.response_options.set_type("string")
        self.response_options.set_length(length)

    """
    input types with 'different response choices'

    Those methods require an instance of ResponseOptions as input and
    it will replace the one initialized in the construction.

    Most likely a bad idea and a confusing API from the user perpective:
    probably better to set the input type and then let the user construct
    the response choices via calls to the methods of

        self.response_options
    """

    def set_input_type_as_radio(self, response_options: ResponseOption):
        self.set_input_type_rasesli("radio", response_options)

    def set_input_type_as_select(self, response_options: ResponseOption):
        self.set_input_type_rasesli("select", response_options)

    def set_input_type_as_slider(self, response_options: ResponseOption):
        self.set_input_type_rasesli("slider", response_options)

    def set_input_type_rasesli(self, arg0, response_options: ResponseOption):
        self.schema["ui"]["inputType"] = arg0
        response_options.set_type("integer")
        self.response_options = response_options

    """
    UI
    """
    # are input_type and read_only specific properties to items
    # or should they be brought up into the base class?
    # or be made part of an UI class?

    # def set_input_type(self, input_type):
    #     self.schema["ui"]["inputType"] = input_type

    def set_read_only_value(self, value):
        self.schema["ui"]["readonlyValue"] = value

    """
    writing, reading, sorting, unsetting
    """

    def set_response_options(self):
        """
        Passes the content of the response options to the schema of the item.
        To be done before writing the item
        """
        self.schema["responseOptions"] = self.response_options.options

    def unset(self, keys):
        """
        Mostly used to remove some empty keys from the schema. Rarely used.
        """
        for i in keys:
            self.schema.pop(i, None)

    def write(self, output_dir):
        self.sort()
        self.set_response_options()
        self._SchemaBase__write(output_dir)

    def sort(self):
        self.sort_schema()
