# Mappings for converting OpenDataCapture (ODC) form instrument to ReproSchema

# ODC field categories (kind) to XSD value types
ODC_VALUE_TYPE_MAP = {
    "string": "xsd:string",
    "number": "xsd:decimal",
    "boolean": "xsd:boolean",
    "date": "xsd:date",
    "set": "xsd:string",  # Set maps to choices, but value is string
    "record-array": "xsd:string",  # Complex type, handled specially
    "number-record": "xsd:integer",  # Often used for Likert rows
    "dynamic": "xsd:string",  # Skip with warning, but define type
}

# ODC (kind, variant) to ReproSchema input types
ODC_INPUT_TYPE_MAP = {
    # kind: {variant: inputType}
    "string": {
        "input": "text",
        "textarea": "text",
        "password": "text",
        "radio": "radio",
        "select": "select",
    },
    "number": {
        "input": "number",
        "slider": "slider",
        "radio": "radio",
        "select": "select",
    },
    "boolean": {
        "checkbox": "checkbox",
        "radio": "radio",
    },
    "date": {
        "None": "date",  # Variant may be null for date
    },
    "set": {
        "listbox": "select",
        "select": "select",
    },
    "number-record": {
        "likert": "radio",  # Each row in likert is a radio selection
    },
}

# ODC field properties to internal names
ODC_COLUMN_MAP = {
    "label": "question",
    "description": "description",
    "instructions": "instruction",
}


def get_odc_input_type(kind: str, variant: str = None) -> str:
    """
    Get ReproSchema input type from ODC kind and variant.

    Args:
        kind: ODC field kind
        variant: ODC field variant

    Returns:
        ReproSchema input type
    """
    if not kind:
        return "text"

    kind = kind.lower().strip()
    variant = str(variant).lower().strip() if variant else "None"

    if kind in ODC_INPUT_TYPE_MAP:
        variants = ODC_INPUT_TYPE_MAP[kind]
        if variant in variants:
            return variants[variant]
        # Default for the kind if variant not matched
        if "None" in variants:
            return variants["None"]
        # If no default, pick the first one if it exists
        if variants:
            return list(variants.values())[0]

    return "text"


def get_odc_value_type(kind: str) -> str:
    """
    Get XSD value type from ODC kind.

    Args:
        kind: ODC field kind

    Returns:
        XSD value type string
    """
    if not kind:
        return "xsd:string"

    kind = kind.lower().strip()

    if kind in ODC_VALUE_TYPE_MAP:
        return ODC_VALUE_TYPE_MAP[kind]

    return "xsd:string"


def is_multiple_choice(kind: str, variant: str = None) -> bool:
    """
    Check if an ODC field is a multiple choice selection.

    Args:
        kind: ODC field kind
        variant: ODC field variant

    Returns:
        True if field supports multiple choice
    """
    if not kind:
        return False

    kind = kind.lower().strip()
    variant = str(variant).lower().strip() if variant else ""

    # 'set' in ODC always allows multiple choices
    if kind == "set":
        return True

    return False
