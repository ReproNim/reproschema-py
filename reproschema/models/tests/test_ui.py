from collections import OrderedDict

from reproschema.models.ui import UI


def test_field():
    a = UI(at_type="reproschema:Field")
    assert a.schema_order == ["inputType", "readonlyValue"]
    print(a.schema)
    assert a.schema == OrderedDict()


def test_protocol():
    a = UI(at_type="reproschema:Protocol", shuffle=False)
    assert a.schema == OrderedDict(
        {
            "shuffle": False,
            "allow": ["reproschema:AutoAdvance", "reproschema:AllowExport"],
        }
    )
