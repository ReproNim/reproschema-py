# mappings.py

CSV_TO_REPROSCHEMA_MAP = {
    "activity_name": "Source From",
    "item_name": "Name",
    "inputType": "Field Type",
    "question": "Question",
    "response_option": "Option Values",
    "branch_logic": "REDCap Branching Logic",
    "description": "Description",
    "valueRequired": "REDCap Field Required",
    "validation": "Data Type",
}

VALUE_TYPE_MAP = {
    "String": "xsd:string",
    "Enum": "xsd:enumeration",
    "Date": "xsd:date",
    "Time": "xsd:dateTime",
    "Numeric": "xsd:decimal",
    "Float": "xsd:decimal",
    "Integer": "xsd:integer",
    "Static": "xsd:string",
}

INPUT_TYPE_MAP = {
    "Numeric": "number",
    "Checkbox": "text",
    "Multi-select": "select",
    "Dropdown": "select",
    "Text": "text",
}

ADDITIONAL_NOTES_LIST = [
    "Domain",
    "Study",
    "Field Class",
    "Field Category",
    "Data Scope",
    "Source/Respondent",
    "Description Status",
]