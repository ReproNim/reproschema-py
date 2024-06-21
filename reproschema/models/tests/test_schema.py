import json
import os
from pathlib import Path

import pytest
from pyld import jsonld

from ...jsonldutils import load_file
from ...utils import start_server, stop_server
from .. import Activity, Item, Protocol, ResponseOption
from ..utils import write_obj_jsonld

contextfile_url = "https://raw.githubusercontent.com/ReproNim/reproschema/ref/linkml/contexts/reproschema"


@pytest.fixture
def server_http_kwargs(request):
    http_kwargs = {}
    stop, port = start_server()
    http_kwargs["port"] = port

    olddir = os.getcwd()
    os.chdir(os.path.dirname(__file__))

    def stoping_server():
        stop_server(stop)
        os.chdir(olddir)

    request.addfinalizer(stoping_server)
    return http_kwargs


@pytest.mark.parametrize(
    "model_class", [Protocol, Activity, Item, ResponseOption]
)
def test_constructors(model_class):
    ob = model_class()
    assert hasattr(ob, "id")
    assert hasattr(ob, "category")


def test_protocol(tmp_path, server_http_kwargs):
    """check if protocol is created correctly for a simple example
    and if it can be written to the file as jsonld.
    """
    protocol_dict = {
        "category": "Protocol",
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
    protocol_obj = Protocol(**protocol_dict)

    # writing to the file
    file_path = tmp_path / "protocol1.jsonld"
    write_obj_jsonld(protocol_obj, file_path, contextfile_url)

    # loading data from the file and checking if this is the same as initial dictionary
    data_comp = load_file(
        file_path,
        started=True,
        http_kwargs=server_http_kwargs,
        compact=True,
        compact_context=contextfile_url,
    )
    del data_comp["@context"]
    assert protocol_dict == data_comp


def test_activity(tmp_path, server_http_kwargs):
    """check if activity is created correctly for a simple example
    and if it can be written to the file as jsonld."""
    activity_dict = {
        "category": "Activity",
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
            {
                "variableName": "activity1_total_score",
                "jsExpression": "item1 + item2",
            }
        ],
    }
    activity_obj = Activity(**activity_dict)

    file_path = tmp_path / "activity1.jsonld"
    write_obj_jsonld(activity_obj, file_path, contextfile_url)

    # loading data from the file and checking if this is the same as initial dictionary
    data_comp = load_file(
        file_path,
        started=True,
        http_kwargs=server_http_kwargs,
        compact=True,
        compact_context=contextfile_url,
    )
    del data_comp["@context"]
    assert activity_dict == data_comp


def test_item(tmp_path, server_http_kwargs):
    """check if item is created correctly for a simple example"
    and if it can be written to the file as jsonld."""

    item_dict = {
        "category": "Field",
        "id": "item1.jsonld",
        "prefLabel": {"en": "item1"},
        "altLabel": {"en": "item1_alt"},
        "description": {"en": "Q1 of example 1"},
        "schemaVersion": "1.0.0-rc4",
        "version": "0.0.1",
        "audio": {
            "category": "AudioObject",
            "contentUrl": "http://media.freesound.org/sample-file.mp4",
        },
        "image": {
            "category": "ImageObject",
            "contentUrl": "http://example.com/sample-image.jpg",
        },
        "question": {
            "en": "Little interest or pleasure in doing things",
            "es": "Poco interés o placer en hacer cosas",
        },
        # "ui": {"inputType": "radio"},
        "responseOptions": {
            "minValue": 0,
            "maxValue": 3,
            "multipleChoice": False,
            "choices": [
                {
                    "name": {"en": "Not at all", "es": "Para nada"},
                    "value": "a",
                },
                {
                    "name": {"en": "Several days", "es": "Varios días"},
                    "value": "b",
                },
            ],
        },
    }

    item_obj = Item(**item_dict)

    file_path = tmp_path / "item1.jsonld"
    write_obj_jsonld(item_obj, file_path, contextfile_url)

    # loading data from the file and checking if this is the same as initial dictionary
    data_comp = load_file(
        file_path,
        started=True,
        http_kwargs=server_http_kwargs,
        compact=True,
        compact_context=contextfile_url,
    )
    del data_comp["@context"]
    assert item_dict == data_comp
