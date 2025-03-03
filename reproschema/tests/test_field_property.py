import pytest

from ..redcap2reproschema import process_row
from ..redcap_mappings import REDCAP_COLUMN_MAP


def update_keys(data):
    """Update keys in the dictionary to match the expected keys in the reproschema"""
    # Add default value for "Field Label" if it is not present
    if "Field Label" not in data:
        data["Field Label"] = "question"
    # Update keys to match the expected keys in the reproschema
    updated_data = {}
    for key, value in data.items():
        updated_data[REDCAP_COLUMN_MAP[key]] = value
    return updated_data


@pytest.mark.parametrize(
    "field_data,expected",
    [
        # Test case 1: No branching logic or annotations
        ({"Variable / Field Name": "test_field"}, True),
        # Test case 2: With branching logic
        (
            {
                "Variable / Field Name": "test_field",
                "Branching Logic (Show field only if...)": "[age] > 18",
            },
            "age > 18",
        ),
        # Test case 3: With @HIDDEN annotation
        (
            {
                "Variable / Field Name": "test_field",
                "Field Annotation": "@HIDDEN",
            },
            False,
        ),
        # Test case 4: With both branching logic and @HIDDEN
        (
            {
                "Variable / Field Name": "test_field",
                "Branching Logic (Show field only if...)": "[age] > 18",
                "Field Annotation": "@HIDDEN",
            },
            False,
        ),
    ],
)
def test_process_field_properties_visibility(field_data, expected):
    # Test case 1: No branching logic or annotations
    _, _, _, add_prop = process_row(update_keys(field_data))
    if expected is True:
        assert add_prop.get("isVis", True) is True  # defaults is True
    else:
        assert add_prop.get("isVis") == expected


@pytest.mark.parametrize(
    "input,expected",
    [
        # CALCTEXT with conditional logic
        (
            {
                "Variable / Field Name": "parkinsons_diagnosis",
                "Required Field?": "",
                "Field Annotation": "@CALCTEXT(if(([diagnosis_parkinsons_gsd_category_1(bradykinesia)] && ([diagnosis_parkinsons_gsd_category_1(tremor)] || [diagnosis_parkinsons_gsd_category_1(rigidity)])), 'Yes', 'No'))",
                "Branching Logic (Show field only if...)": "[some_other_condition] = 1",
            },
            {
                "variableName": "parkinsons_diagnosis",
                "isAbout": "items/parkinsons_diagnosis",
                "isVis": False,
            },
        ),
        # CALCTEXT with numerical operations
        (
            {
                "Variable / Field Name": "bmi",
                "Required Field?": "",
                "Field Annotation": "@CALCTEXT([weight]/([height]*[height]))",
                "Branching Logic (Show field only if...)": "[weight] > 0 and [height] > 0",
            },
            {
                "variableName": "bmi",
                "isAbout": "items/bmi",
                "isVis": False,
            },
        ),
        # CALCTEXT with multiple nested conditions
        (
            {
                "Variable / Field Name": "complex_score",
                "Required Field?": "",
                "Field Annotation": "@CALCTEXT(if([score1] > 10 && [score2] < 5, 'High', if([score1] > 5, 'Medium', 'Low')))",
                "Branching Logic (Show field only if...)": "",
            },
            {
                "variableName": "complex_score",
                "isAbout": "items/complex_score",
                "isVis": False,
            },
        ),
    ],
)
def test_process_field_properties_calctext(input, expected):
    """Test different CALCTEXT annotations with realistic examples"""
    _, _, _, add_prop = process_row(update_keys(input))
    for key, expected_value in expected.items():
        assert (
            add_prop[key] == expected_value
        ), f"Failed for {key} in test case with annotation: {input['Field Annotation']}"


@pytest.mark.parametrize(
    "input,expected",
    [
        # CALCTEXT with READONLY
        (
            {
                "Variable / Field Name": "test_var",
                "Required Field?": "",
                "Field Annotation": "@CALCTEXT @READONLY",
                "Branching Logic (Show field only if...)": "",
            },
            {"isVis": False},
        ),
        # CALCTEXT with HIDDEN
        (
            {
                "Variable / Field Name": "test_var",
                "Required Field?": "",
                "Field Annotation": "@HIDDEN @CALCTEXT(if([var1] > 0, 1, 0))",
                "Branching Logic (Show field only if...)": "",
            },
            {"isVis": False},
        ),
        # Complex CALCTEXT with other annotations
        (
            {
                "Variable / Field Name": "test_var",
                "Required Field?": "",
                "Field Annotation": "@CALCTEXT(if(([var1] && [var2]), 'Yes', 'No')) @READONLY @HIDDEN-SURVEY",
                "Branching Logic (Show field only if...)": "[condition] = 1",
            },
            {"isVis": False},
        ),
    ],
)
def test_process_field_properties_mixed_annotations(input, expected):
    """Test fields with multiple annotations"""
    _, _, _, add_prop = process_row(update_keys(input))
    for key, expected_value in expected.items():
        assert (
            add_prop[key] == expected_value
        ), f"Failed for {key} in test case with annotation: {input['Field Annotation']}"
