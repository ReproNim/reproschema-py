# All the mapping used in the code
REDCAP_COLUMN_MAP = {
    "Variable / Field Name": "item_name",  # column A
    "Form Name": "activity_name",  # column B
    "Section Header": "preamble",  # column C
    "Field Type": "inputType",  # column D
    "Field Label": "question",  # column E
    "Choices, Calculations, OR Slider Labels": "choices",  # column F
    "Field Note": "note",  # column G
    "Text Validation Type OR Show Slider Number": "validation",  # column H
    "Text Validation Min": "minValue",  # column I
    "Text Validation Max": "maxValue",  # column J
    "Identifier?": "identifiable",  # column K
    "Branching Logic (Show field only if...)": "visibility",  # column L
    "Required Field?": "valueRequired",  # column M
    "Custom Alignment": "customAlignment",  # column N
    "Question Number (surveys only)": "questionNumber",  # column O
    "Matrix Group Name": "matrixGroup",  # column P
    "Matrix Ranking?": "matrixRanking",  # column Q
    "Field Annotation": "annotation",  # column R
}
# REDCAP_COLUMN_MAP_REVERSE = {v: k for k, v in REDCAP_COLUMN_MAP.items()}

REDCAP_COLUMN_REQUIRED = [
    "Variable / Field Name",
    "Form Name",
    "Field Type",
    "Field Label",
    "Choices, Calculations, OR Slider Labels",
]

INPUT_TYPE_MAP = {
    "calc": "number",
    "sql": "number",
    "yesno": "radio",
    "radio": "radio",
    "checkbox": "radio",
    "descriptive": "static",
    "dropdown": "select",
    "text": "text",
    "notes": "text",
    "file": "documentUpload",
    "slider": "slider",
}

# Map certain field types directly to xsd types
VALUE_TYPE_MAP = {
    "text": "xsd:string",
    "date_": "xsd:date",
    "date_mdy": "xsd:date",  # it's not exactly xsd:date
    "datetime_seconds_mdy": "xsd:date",  # it's not exactly xsd:date
    "date_ymd": "xsd:date",
    "date_dmy": "xsd:date",
    "datetime_": "xsd:dateTime",
    "datetime_ymd": "xsd:dateTime",
    "time_": "xsd:time",
    "email": "xsd:string",
    "phone": "xsd:string",
    "number": "xsd:decimal",  # could be an integer, but have no idea of knowing)
    "float": "xsd:decimal",
    "integer": "xsd:integer",
    "signature": "xsd: string",
    "zipcode": "xsd: string",
    "autocomplete": "xsd: string",
}

# field types that should be used as compute
COMPUTE_LIST = ["calc", "sql"]
RESPONSE_COND = ["minValue", "maxValue"]
ADDITIONAL_NOTES_LIST = [
    "Field Note",
    "Question Number (surveys only)",
    "Matrix Group Name",
    "Matrix Ranking?",
    "Text Validation Type OR Show Slider Number",
    "Text Validation Min",
    "Text Validation Max",
    "Identifier?",
    "Custom Alignment",
    "Question Number (surveys only)",
    "Field Annotation",
]
