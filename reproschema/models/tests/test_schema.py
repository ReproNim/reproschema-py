from .. import Protocol, Activity, Item, ResponseOption
import pytest


@pytest.mark.parametrize("model_class", [Protocol, Activity, Item, ResponseOption])
def test_constructors(model_class):
    ob = model_class()
    assert hasattr(ob, "id")
    assert hasattr(ob, "category")
