# from .. import Protocol, Activity, Item
from .. import activity, protocol, item

def test_constructors():
    protocol.Protocol()
    activity.Activity()

    version = "1.0.0-rc4"
    proto = protocol.Protocol(version=version)
    assert proto.schema["schemaVersion"] == version
    act = activity.Activity(version)
    assert act.schema["schemaVersion"] == version
    # item = item.Item(version)
    # assert item.schema["schemaVersion"] == version


def test_constructors_from_data():
    protocol.Protocol.from_data({"@type": "reproschema:Protocol"})
    activity.Activity.from_data({"@type": "reproschema:Activity"})
    # item.Item.from_data({"@type": "reproschema:Field"})
