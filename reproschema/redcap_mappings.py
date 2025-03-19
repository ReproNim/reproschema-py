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
REDCAP_COLUMN_MAP_REVERSE = {v: k for k, v in REDCAP_COLUMN_MAP.items()}

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
    "truefalse": "radio",
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
    # Basic types
    "text": "xsd:string",
    "email": "xsd:string",
    "phone": "xsd:string",
    "signature": "xsd:string",
    "zipcode": "xsd:string",
    "autocomplete": "xsd:string",
    # Numeric types
    "number": "xsd:decimal",  # This includes both integer and float, redcap use for both
    "float": "xsd:decimal",
    "integer": "xsd:integer",
    # Date and time types will be handled by pattern matching in process_input_value_types
    # These entries are kept for backward compatibility
    "date_": "xsd:date",
    "time_": "xsd:time",
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


def get_value_type(validation_type):
    """
    Determine the XSD value type based on REDCap validation type

    Args:
        validation_type (str): Validation type from REDCap

    Returns:
        str: XSD value type for ReproSchema
    """
    # Handle date and time formats with pattern matching
    if validation_type.startswith("date_"):
        return "xsd:date"
    elif validation_type.startswith("datetime_"):
        return "xsd:dateTime"
    elif validation_type.startswith("time"):
        return "xsd:time"
    elif validation_type in VALUE_TYPE_MAP:
        return VALUE_TYPE_MAP[validation_type]
    else:
        raise ValueError(
            f"Validation type: {validation_type} is not supported yet. "
            "Please add it to VALUE_TYPE_MAP."
        )
