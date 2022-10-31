from reproschema.models import Activity
from reproschema.models import Item
from reproschema.models import Protocol


def test_constructors():
    Protocol()
    Activity()
    Item()
    version = "1.0.0-rc2"
    proto = Protocol(schemaVersion=version)
    assert proto.schema["schemaVersion"] == version
    act = Activity(schemaVersion=version)
    assert act.schema["schemaVersion"] == version
    item = Item(schemaVersion=version)
    assert item.schema["schemaVersion"] == version


def test_constructors_from_data():
    Protocol.from_data({"@type": "reproschema:Protocol"})
    Activity.from_data({"@type": "reproschema:Activity"})
    Item.from_data({"@type": "reproschema:Field"})
