from .base import SchemaBase


DEFAULT_LANG = "en"


class Item(SchemaBase):
    """
    class to deal with reproschema items
    """

    schema_type = "reproschema:Field"

    def __init__(self, version=None):
        super().__init__(version)
        self.schema["ui"] = {"inputType": []}
        self.schema["question"] = {}
        self.schema["responseOptions"] = {}
        self.response_options = ResponseOption()
        # default input type is "text"
        self.set_input_type_as_text()

    def set_URI(self, URI):
        self.URI = URI

    # TODO
    # image
    # readonlyValue

    def set_defaults(self, name="default"):
        self._SchemaBase__set_defaults(name)
        self.set_filename(name)
        self.set_input_type_as_text()

    def set_filename(self, name, ext=".jsonld"):
        self.schema_file = name + ext
        self.schema["@id"] = name + ext

    def set_question(self, question, lang=DEFAULT_LANG):
        self.schema["question"][lang] = question

    def set_input_type(self, input_type):
        self.schema["ui"]["inputType"] = input_type

    def set_response_options(self):
        self.schema["responseOptions"] = self.response_options.options

    """
    input types with different response choices
    """

    def set_input_type_as_radio(self, response_options):
        self.set_input_type("radio")
        self.response_options = response_options
        self.set_response_options()

    def set_input_type_as_select(self, response_options):
        self.set_input_type("select")
        self.response_options = response_options
        self.set_response_options()

    def set_input_type_as_slider(self):
        self.set_input_type_as_text()  # until the slide item of the ui is fixed
        # self.set_input_type("slider")
        # self.set_response_options({"valueType": "xsd:string"})

    def set_input_type_as_language(self):

        URL = "https://raw.githubusercontent.com/ReproNim/reproschema/"

        self.set_input_type("selectLanguage")

        self.response_options.set_type("str")
        self.response_options.set_multiple_choice(True)
        self.response_options["options"]["choices"] = (
            URL + "master/resources/languages.json"
        )

        self.set_response_options()

    """
    input types with no response choice
    """

    def set_input_type_as_int(self):
        self.set_input_type("number")
        self.response_options.set_type("int")
        self.response_options.options.pop("maxLength", None)

    def set_input_type_as_float(self):
        self.set_input_type("float")
        self.response_options.set_type("float")
        self.response_options.options.pop("maxLength", None)

    def set_input_type_as_time_range(self):
        self.set_input_type("timeRange")
        self.set_response_options({"valueType": "datetime"})

    def set_input_type_as_date(self):
        self.set_input_type("date")
        self.set_response_options({"valueType": "xsd:date"})

    """
    input types with no response choice but with some parameters
    """

    def set_input_type_as_text(self, length=300):
        self.set_input_type("text")
        self.response_options.set_type("str")
        self.response_options.set_length(length)
        self.response_options.options.pop("maxValue", None)
        self.response_options.options.pop("minValue", None)
        self.response_options.options.pop("multipleChoice", None)
        self.response_options.options.pop("choices", None)
        self.set_response_options()

    def set_input_type_as_multitext(self, length=300):
        self.set_input_type("multitext")
        self.response_options.set_type("str")
        self.response_options.set_length(length)
        self.set_response_options()

    # TODO
    # email: EmailInput/EmailInput.vue
    # audioCheck: AudioCheck/AudioCheck.vue
    # audioRecord: WebAudioRecord/Audio.vue
    # audioPassageRecord: WebAudioRecord/Audio.vue
    # audioImageRecord: WebAudioRecord/Audio.vue
    # audioRecordNumberTask: WebAudioRecord/Audio.vue
    # audioAutoRecord: AudioCheckRecord/AudioCheckRecord.vue
    # year: YearInput/YearInput.vue
    # selectCountry: SelectInput/SelectInput.vue
    # selectState: SelectInput/SelectInput.vue
    # documentUpload: DocumentUpload/DocumentUpload.vue
    # save: SaveData/SaveData.vue
    # static: Static/Static.vue
    # StaticReadOnly: Static/Static.vue

    def set_basic_response_type(self, response_type):

        # default (also valid for "char" input type)
        self.set_input_type_as_char()

        if response_type == "int":
            self.set_input_type_as_int()

        elif response_type == "float":
            self.set_input_type_as_float()

        elif response_type == "date":
            self.set_input_type_as_date()

        elif response_type == "time range":
            self.set_input_type_as_time_range()

        elif response_type == "language":
            self.set_input_type_as_language()

    """
    writing and sorting of dictionaries
    """

    def write(self, output_dir):
        self.sort()
        self._SchemaBase__write(output_dir)

    def sort(self):
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
        self.sort_schema(schema_order)


class ResponseOption:
    """
    class to deal with reproschema response options
    """

    def __init__(self):
        self.options = {
            "valueType": "",
            "minValue": 0,
            "maxValue": 0,
            "choices": [],
            "multipleChoice": False,
        }

        # "readonlyValue": False,
        # "maxLength": 0,

    def set_type(self, type):
        if type == "int":
            self.options["valueType"] = "xsd:integer"
        elif type == "str":
            self.options["valueType"] = "xsd:string"
        elif type == "float":
            self.options["valueType"] = "xsd:float"
        elif type == "date":
            self.options["valueType"] = "xsd:date"
        elif type == "datetime":
            self.options["valueType"] = "datetime"

    def set_input_type_as_date(self):
        self.set_input_type("date")
        self.set_response_options({"valueType": "xsd:date"})

    def set_min(self, value):
        self.options["minValue"] = value

    def set_max(self, value):
        self.options["maxValue"] = value

    def set_length(self, value):
        self.options["maxLength"] = value

    def set_multiple_choice(self, value):
        self.options["multipleChoice"] = value

    def add_choice(self, choice):
        self.options["choices"].append(choice)
