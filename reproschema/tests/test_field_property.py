import csv

import pytest

from ..redcap2reproschema import process_field_properties


def test_process_field_properties_calctext():
    """Test different CALCTEXT annotations with realistic examples"""
    test_cases = [
        # Simple CALCTEXT
        {
            "input": {
                "Variable / Field Name": "test_var",
                "Required Field?": "",
                "Field Annotation": "@CALCTEXT",
                "Branching Logic (Show field only if...)": "",
            },
            "expected": {
                "variableName": "test_var",
                "isAbout": "items/test_var",
                "isVis": False,
            },
        },
        # Complex CALCTEXT with conditional logic
        {
            "input": {
                "Variable / Field Name": "parkinsons_diagnosis",
                "Required Field?": "",
                "Field Annotation": "@CALCTEXT(if(([diagnosis_parkinsons_gsd_category_1(bradykinesia)] && ([diagnosis_parkinsons_gsd_category_1(tremor)] || [diagnosis_parkinsons_gsd_category_1(rigidity)])), 'Yes', 'No'))",
                "Branching Logic (Show field only if...)": "[some_other_condition] = 1",
            },
            "expected": {
                "variableName": "parkinsons_diagnosis",
                "isAbout": "items/parkinsons_diagnosis",
                "isVis": False,
            },
        },
        # CALCTEXT with numerical operations
        {
            "input": {
                "Variable / Field Name": "bmi",
                "Required Field?": "",
                "Field Annotation": "@CALCTEXT([weight]/([height]*[height]))",
                "Branching Logic (Show field only if...)": "[weight] > 0 and [height] > 0",
            },
            "expected": {
                "variableName": "bmi",
                "isAbout": "items/bmi",
                "isVis": False,
            },
        },
        # CALCTEXT with multiple nested conditions
        {
            "input": {
                "Variable / Field Name": "complex_score",
                "Required Field?": "",
                "Field Annotation": "@CALCTEXT(if([score1] > 10 && [score2] < 5, 'High', if([score1] > 5, 'Medium', 'Low')))",
                "Branching Logic (Show field only if...)": "",
            },
            "expected": {
                "variableName": "complex_score",
                "isAbout": "items/complex_score",
                "isVis": False,
            },
        },
    ]

    for test_case in test_cases:
        result = process_field_properties(test_case["input"])
        for key, expected_value in test_case["expected"].items():
            assert (
                result[key] == expected_value
            ), f"Failed for {key} in test case with annotation: {test_case['input']['Field Annotation']}"


def test_process_field_properties_mixed_annotations():
    """Test fields with multiple annotations"""
    test_cases = [
        # CALCTEXT with READONLY
        {
            "input": {
                "Variable / Field Name": "test_var",
                "Required Field?": "",
                "Field Annotation": "@CALCTEXT @READONLY",
                "Branching Logic (Show field only if...)": "",
            },
            "expected": {"isVis": False},
        },
        # CALCTEXT with HIDDEN
        {
            "input": {
                "Variable / Field Name": "test_var",
                "Required Field?": "",
                "Field Annotation": "@HIDDEN @CALCTEXT(if([var1] > 0, 1, 0))",
                "Branching Logic (Show field only if...)": "",
            },
            "expected": {"isVis": False},
        },
        # Complex CALCTEXT with other annotations
        {
            "input": {
                "Variable / Field Name": "test_var",
                "Required Field?": "",
                "Field Annotation": "@CALCTEXT(if(([var1] && [var2]), 'Yes', 'No')) @READONLY @HIDDEN-SURVEY",
                "Branching Logic (Show field only if...)": "[condition] = 1",
            },
            "expected": {"isVis": False},
        },
    ]

    for test_case in test_cases:
        result = process_field_properties(test_case["input"])
        for key, expected_value in test_case["expected"].items():
            assert (
                result[key] == expected_value
            ), f"Failed for {key} in test case with annotation: {test_case['input']['Field Annotation']}"
