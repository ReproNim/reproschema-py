from .. import activity_new, protocol_new

def test_constructors():
    protocol_new.Protocol()
    activity_new.Activity()

    version = "1.0.0-rc4"
    proto = protocol_new.Protocol(version=version)
    assert proto.schemaVersion == version
    assert proto.schema_type == "reproschema:Protocol"
    act = activity_new.Activity(version=version)
    assert act.schemaVersion == version
    assert act.schema_type == "reproschema:Activity"


def test_constructors_from_data():
    protocol_new.Protocol.from_data({"@type": "reproschema:Protocol"}, "reproschema:Protocol")
    activity_new.Activity.from_data({"@type": "reproschema:Activity"}, "reproschema:Activity")

