from .. import Protocol, Activity, Item, ResponseOption
import pytest


@pytest.mark.parametrize("model_class", [Protocol, Activity, Item, ResponseOption])
def test_constructors(model_class):
    ob = model_class()
    assert hasattr(ob, "id")
    assert hasattr(ob, "category")


def test_protocol():
    """check if protocol is created correctly for a simple example"""
    protocol_dict = {
        "category": "reproschema:Protocol",
        "id": "protocol1.jsonld",
        "prefLabel": {"en": "Protocol1", "es": "Protocol1_es"},
        "description": {"en": "example Protocol"},
        "schemaVersion": "1.0.0-rc4",
        "version": "0.0.1",
        "messages": [
            {
                "message": {
                    "en": "Test message: Triggered when item1 value is greater than 0"
                },
                "jsExpression": "item1 > 0",
            }
        ],
    }
    Protocol(**protocol_dict)


def test_activity():
    """check if activity is created correctly for a simple example"""
    activity_dict = {
        "category": "reproschema:Activity",
        "id": "activity1.jsonld",
        "prefLabel": {"en": "Example 1"},
        "description": {"en": "Activity example 1"},
        "schemaVersion": "1.0.0-rc4",
        "version": "0.0.1",
        "image": {
            "category": "AudioObject",
            "contentUrl": "http://example.com/sample-image.png",
        },
        "preamble": {
            "en": "Over the last 2 weeks, how often have you been bothered by any of the following problems?",
            "es": "Durante las últimas 2 semanas, ¿con qué frecuencia le han molestado los siguintes problemas?",
        },
        "compute": [
            {"variableName": "activity1_total_score", "jsExpression": "item1 + item2"}
        ],
    }
    Activity(**activity_dict)


def test_item():
    """check if item is created correctly for a simple example"""

    item_dict = {
        "category": "reproschema:Field",
        "id": "item1.jsonld",
        "prefLabel": "item1",
        "altLabel": "item1_alt",
        "description": "Q1 of example 1",
        "schemaVersion": "1.0.0-rc4",
        "version": "0.0.1",
        "audio": {
            "@type": "AudioObject",
            "contentUrl": "http://media.freesound.org/sample-file.mp4",
        },
        "image": {
            "@type": "ImageObject",
            "contentUrl": "http://example.com/sample-image.jpg",
        },
        "question": {
            "en": "Little interest or pleasure in doing things",
            "es": "Poco interés o placer en hacer cosas",
        },
        "ui": {"inputType": "radio"},
        "responseOptions": {
            "valueType": "xsd:integer",
            "minValue": 0,
            "maxValue": 3,
            "multipleChoice": False,
            "choices": [
                {"name": {"en": "Not at all", "es": "Para nada"}, "value": 0},
                {"name": {"en": "Several days", "es": "Varios días"}, "value": "a"},
            ],
        },
    }
