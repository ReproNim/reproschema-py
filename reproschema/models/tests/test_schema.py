from .. import Protocol, Activity, Item


def test_constructors():
    Protocol()
    Activity()
    Item()
    version = "1.0.0-rc2"
    proto = Protocol(version=version)
    assert proto.schema["schemaVersion"] == version
    act = Activity(version)
    assert act.schema["schemaVersion"] == version
    item = Item(version)
    assert item.schema["schemaVersion"] == version


def test_constructors_from_data():
    Protocol.from_data({"@type": "reproschema:Protocol"})
    Activity.from_data({"@type": "reproschema:Activity"})
    Item.from_data({"@type": "reproschema:Field"})
