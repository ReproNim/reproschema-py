from .base import SchemaBase


DEFAULT_LANG = "en"


class Item(SchemaBase):
    """
    class to deal with reproschema items
    """

    schema_type = "reproschema:Field"
    visible = True
    required = False
    skippable = True

    def __init__(self, version=None):
        super().__init__(version)
        self.schema["ui"] = {"inputType": []}
        self.schema["question"] = {}
        """
        The responseOptions dictionnary is kept empty until the file has to be written
        then it gets its content wit the method `set_response_options`
        from the `options` dictionnary of an instance of the ResponseOptions class that is kept in
        ``self.response_options``
        """
        self.schema["responseOptions"] = {}
        self.response_options = ResponseOption()

        # default input type is "text"
        self.set_input_type_as_text()

    def set_defaults(self, name="default"):
        self._SchemaBase__set_defaults(name)
        self.set_filename(name)
        self.set_input_type_as_text()

    def set_filename(self, name, ext=".jsonld"):
        """
        Note there is no _schema suffix for items names
        """
        name = name.replace(" ", "_")
        self.schema_file = name + ext
        self.schema["@id"] = name + ext

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

    def set_basic_response_type(self, response_type):
        """
        Handles the dispatching to other methods for specific item creations
        Does not cover all items types (maybe it should as this would help
        from an API point of view to pass everything through this function)
        The default is "text" input type
        """
        self.set_input_type_as_text()

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
    input types with different response choices

    For many items it is necessary to call

        self.response_options.unset

    To remove unecessary or unwanted keys from the response_options
    dictionary.
    Many of those are put there by the constructor of that set
    the default input type as ``self.set_input_type_as_text()``
    so it might be better to maybe have a more minimalistic constructor.

    """

    def set_input_type_as_int(self):
        self.set_input_type("number")
        self.response_options.set_type("integer")
        self.response_options.unset(["maxLength"])

    def set_input_type_as_float(self):
        self.set_input_type("float")
        self.response_options.set_type("float")
        self.response_options.unset(["maxLength"])

    def set_input_type_as_date(self):
        self.set_input_type("date")
        self.response_options.unset(["maxLength"])
        self.response_options.set_type("date")

    def set_input_type_as_time_range(self):
        self.set_input_type("timeRange")
        self.response_options.unset(["maxLength"])
        self.response_options.set_type("datetime")

    def set_input_type_as_year(self):
        self.set_input_type("year")
        self.response_options.unset(["maxLength"])
        self.response_options.set_type("date")

    """
    input types with preset response choices
    """

    def set_input_type_as_language(self):

        URL = "https://raw.githubusercontent.com/ReproNim/reproschema-library/"

        self.set_input_type("selectLanguage")

        self.response_options.set_type("string")
        self.response_options.set_multiple_choice(True)
        self.response_options.use_preset(URL + "master/resources/languages.json")
        self.response_options.unset(["maxLength"])

    def set_input_type_as_country(self):

        URL = "https://raw.githubusercontent.com/samayo/country-json/master/src/country-by-name.json"

        self.set_input_type("selectCountry")

        self.response_options.set_type("string")
        self.response_options.use_preset(URL)
        self.response_options.set_length(50)

    def set_input_type_as_state(self):

        URL = "https://gist.githubusercontent.com/mshafrir/2646763/raw/8b0dbb93521f5d6889502305335104218454c2bf/states_hash.json"

        self.set_input_type("selectState")

        self.response_options.set_type("string")
        self.response_options.use_preset(URL)
        self.response_options.unset(["maxLength"])

    """
    input types requiring user typed input
    """

    def set_input_type_as_text(self, length=300):
        self.set_input_type("text")
        self.response_options.set_type("string")
        self.response_options.set_length(length)
        self.response_options.unset(
            ["maxValue", "minValue", "multipleChoice", "choices"]
        )

    def set_input_type_as_multitext(self, length=300):
        self.set_input_type("multitext")
        self.response_options.set_type("string")
        self.response_options.set_length(length)

    def set_input_type_as_email(self):
        self.set_input_type("email")
        self.response_options.unset(["maxLength"])

    def set_input_type_as_id(self):
        """
        for participant id items
        """
        self.set_input_type("pid")
        self.response_options.unset(["maxLength"])

    """
    input types with 'different response choices'

    Those methods require an instance of ResponseOptions as input and
    it will replace the one initialized in the construction.

    Most likely a bad idea and a confusing API from the user perpective:
    probably better to set the input type and then let the user construct
    the response choices via calls to the methods of

        self.response_options
    """

    def set_input_type_as_radio(self, response_options):
        self.set_input_type("radio")
        response_options.set_type("integer")
        self.response_options = response_options

    def set_input_type_as_select(self, response_options):
        self.set_input_type("select")
        response_options.set_type("integer")
        self.response_options = response_options

    def set_input_type_as_slider(self, response_options):
        self.set_input_type("slider")
        response_options.set_type("integer")
        self.response_options = response_options

    """
    UI
    """
    # are input_type and read_only specific properties to items
    # or should they be brought up into the base class?
    # or be made part of an UI class?

    def set_input_type(self, input_type):
        self.schema["ui"]["inputType"] = input_type

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


class ResponseOption(SchemaBase):
    """
    class to deal with reproschema response options
    """

    # TODO
    # the dictionnary that keeps track of the content of the response options should
    # be called "schema" and not "options" so as to be able to make proper use of the
    # methods of the parent class and avoid copying content between
    #
    # self.options and self.schema

    schema_type = "reproschema:ResponseOption"

    def __init__(self):
        self.options = {
            "valueType": "",
            "minValue": 0,
            "maxValue": 0,
            "choices": [],
            "multipleChoice": False,
        }

    def set_defaults(self, name="valueConstraints", version=None):
        super().__init__(version)
        self.options["@context"] = self.schema["@context"]
        self.options["@type"] = self.schema_type
        self.set_filename(name)

    def set_filename(self, name, ext=".jsonld"):
        name = name.replace(" ", "_")
        self.schema_file = name + ext
        self.options["@id"] = name + ext

    def unset(self, keys):
        if type(keys) == str:
            keys = [keys]
        for i in keys:
            self.options.pop(i, None)

    def set_type(self, type):
        self.options["valueType"] = "xsd:" + type

    # TODO a nice thing to do would be to read the min and max value
    # from the rest of the content of self.options
    # could avoid having the user to input those
    def set_min(self, value):
        self.options["minValue"] = value

    def set_max(self, value):
        self.options["maxValue"] = value

    def set_length(self, value):
        self.options["maxLength"] = value

    def set_multiple_choice(self, value):
        self.options["multipleChoice"] = value

    def use_preset(self, URI):
        """
        In case the list response options are read from another file
        like for languages, country, state...
        """
        self.options["choices"] = URI

    def add_choice(self, choice, value, lang=DEFAULT_LANG):
        """
        Add a response option
        """
        # TODO currently a certain response option can only be appended,
        # not removed, no edited
        # Also the current implementation with languages makes it hard for example
        # to query what is the value or question associated with a certain language
        # The nested structure should probably be flattened.
        self.options["choices"].append({"name": {lang: choice}, "value": value})

    def sort(self):
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
        reordered_dict = reorder_dict_skip_missing(self.options, options_order)
        self.options = reordered_dict

    def write(self, output_dir):
        self.sort()
        self.schema = self.options
        self._SchemaBase__write(output_dir)


# TODO
# DUPLICATE from the base class to be used for ResponseOptions sorting of the options
# needs refactoring that will be made easier if the name the ResponseOptions dictionary is
# schema and note options
from collections import OrderedDict


def reorder_dict_skip_missing(old_dict, key_list):
    """
    reorders dictionary according to ``key_list``
    removing any key with no associated value
    or that is not in the key list
    """
    return OrderedDict((k, old_dict[k]) for k in key_list if k in old_dict)
