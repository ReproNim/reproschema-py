# Mappings for converting NBDC data dictionary to ReproSchema

# NBDC column names to ReproSchema internal names
# Based on NBDCtoolsData data dictionary structure
NBDC_COLUMN_MAP = {
    # Primary identifiers
    "name": "item_name",  # Variable name -> item ID
    "table_name": "activity_name",  # Table/assessment -> activity
    # Field properties
    "label": "question",  # Field label/description
    "instruction": "instruction",  # Field instructions
    "header": "preamble",  # Section header
    "note": "note",  # Field notes
    # Data type properties
    "type_var": "inputType",  # Field/input type
    "type_data": "dataType",  # Data type
    "type_level": "levelType",  # Level type
    "type_field": "fieldType",  # Field type metadata
    # Display properties
    "order_display": "orderDisplay",  # Display order
    "order_sort": "orderSort",  # Sort order
    "branching_logic": "visibility",  # Branching/skip logic
    "unit": "unit",  # Unit of measurement
    # Additional metadata
    "table_label": "activity_label",  # Activity display name
    "study": "study",  # Study name
    "domain": "domain",  # Domain
    "sub_domain": "subDomain",  # Sub-domain
    "source": "source",  # Data source
    "metric": "metric",  # Metric name
    "atlas": "atlas",  # Atlas name
}

# Reverse mapping for getting original NBDC column names
NBDC_COLUMN_MAP_REVERSE = {v: k for k, v in NBDC_COLUMN_MAP.items()}

# NBDC input types to ReproSchema input types
# Based on NBDC type_var values from ABCD/HBCD data dictionaries
# The actual type_var values in ABCD data are: administrative, derived, item, item (summary score)
# These describe the field category, not the UI input type
# We also include traditional input type mappings for compatibility
NBDC_INPUT_TYPE_MAP = {
    # NBDC field categories (type_var values)
    "administrative": "static",  # Administrative fields are read-only
    "derived": "number",  # Derived/calculated fields
    "derived item": "number",  # ABCD derived items are computed
    "item": "text",  # Default for standard items (may be overridden by type_data)
    "summary score": "number",  # Summary scores are numeric
    "item (summary score)": "number",  # Deprecated: use "summary score" (kept for compatibility)
    # Text inputs
    "text": "text",
    "alphanumeric": "text",
    "string": "text",
    "textarea": "text",
    "email": "email",
    "phone": "text",
    # Numeric inputs
    "integer": "number",
    "float": "float",
    "decimal": "float",
    "number": "float",
    # Selection inputs
    "select": "select",
    "radio": "radio",
    "dropdown": "select",
    "checkbox": "radio",  # NBDC checkbox maps to radio (single select)
    "multicheckbox": "checkbox",  # Multiple select
    # Boolean
    "yesno": "yesno",
    "truefalse": "truefalse",
    # Special types
    "calculated": "number",  # Calculated fields
    "computed": "text",  # Computed fields
    "descriptive": "static",  # Descriptive text
    "note": "static",  # Notes
    "file": "documentUpload",
    "date": "date",
    "datetime": "dateTime",
    "time": "time",
}

# NBDC data types to XSD value types
# These come from the type_data column in NBDC data dictionaries
NBDC_VALUE_TYPE_MAP = {
    "integer": "xsd:integer",
    "float": "xsd:decimal",
    "decimal": "xsd:decimal",
    "number": "xsd:decimal",
    "string": "xsd:string",
    "text": "xsd:string",
    "alphanumeric": "xsd:string",
    "date": "xsd:date",
    "datetime": "xsd:dateTime",
    "timestamp": "xsd:dateTime",
    "time": "xsd:time",
    "boolean": "xsd:boolean",
    "email": "xsd:string",
    "file": "xsd:anyURI",
    "double": "xsd:decimal",
    "interval": "xsd:string",  # Time interval
}

# Required columns for NBDC data dictionary
NBDC_COLUMN_REQUIRED = [
    "name",
    "table_name",
    "label",
]

# Columns that should be preserved in additionalNotesObj
NBDC_ADDITIONAL_NOTES_COLUMNS = [
    "note",
    "instruction",
    "unit",
    "study",
    "domain",
    "sub_domain",
    "source",
    "metric",
    "atlas",
    "table_nda",
    "table_redcap",
    "name_nda",
    "name_redcap",
    "url_table",
    "url_docs_score",
    "name_short",
    "name_stata",
]

# NBDC-specific field types that should be read-only or computed
# These are based on the type_var column values in ABCD/HBCD data
NBDC_COMPUTE_TYPES = [
    "calculated",
    "computed",
    "derived",  # ABCD derived fields are computed
]

NBDC_READONLY_TYPES = [
    "descriptive",
    "note",
    "administrative",  # ABCD administrative fields are read-only
]


def get_nbdc_input_type(type_var: str, type_data: str = None) -> str:
    """
    Get ReproSchema input type from NBDC type_var.

    Args:
        type_var: NBDC type_var value
        type_data: NBDC type_data value (optional, for more specific typing)

    Returns:
        ReproSchema input type
    """
    if not type_var or not isinstance(type_var, str):
        return "text"

    type_var = type_var.lower().strip()

    # First try direct mapping
    if type_var in NBDC_INPUT_TYPE_MAP:
        return NBDC_INPUT_TYPE_MAP[type_var]

    # Try type_data if available
    if type_data and isinstance(type_data, str):
        type_data = type_data.lower().strip()
        if type_data in NBDC_INPUT_TYPE_MAP:
            return NBDC_INPUT_TYPE_MAP[type_data]

    # Default to text
    return "text"


def get_nbdc_value_type(type_data: str) -> str:
    """
    Get XSD value type from NBDC type_data.

    Args:
        type_data: NBDC type_data value

    Returns:
        XSD value type string
    """
    if not type_data or not isinstance(type_data, str):
        return "xsd:string"

    type_data = type_data.lower().strip()

    if type_data in NBDC_VALUE_TYPE_MAP:
        return NBDC_VALUE_TYPE_MAP[type_data]

    # Default to string
    return "xsd:string"


def is_compute_field(type_var: str) -> bool:
    """
    Check if an NBDC field should be a computed field.

    Args:
        type_var: NBDC type_var value

    Returns:
        True if field should be computed
    """
    if not type_var or not isinstance(type_var, str):
        return False
    return type_var.lower().strip() in NBDC_COMPUTE_TYPES


def is_readonly_field(type_var: str) -> bool:
    """
    Check if an NBDC field should be read-only.

    Args:
        type_var: NBDC type_var value

    Returns:
        True if field should be read-only
    """
    if not type_var or not isinstance(type_var, str):
        return False
    return type_var.lower().strip() in NBDC_READONLY_TYPES
