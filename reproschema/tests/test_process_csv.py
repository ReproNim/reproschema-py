import tempfile
from pathlib import Path

import pandas as pd
import pytest

from ..redcap2reproschema import normalize_condition, process_csv


def test_process_csv():
    csv_data = """Form Name,Variable / Field Name,Field Type,Field Annotation,"Choices, Calculations, OR Slider Labels"
form1,field1,text,,
form1,field2,calc,,[field1] + [field3]
form1,field3,text,@CALCTEXT(3*3),
form2,field4,text,,
,field5,text,,"""

    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = Path(tmpdir) / "test.csv"
        csv_path.write_text(csv_data)

        datas, order, compute = process_csv(csv_path, tmpdir, "test_protocol")

        assert set(datas.keys()) == {"form1", "form2"}
        assert len(datas["form1"]) == 3
        assert len(datas["form2"]) == 1

        assert order["form1"] == [
            "items/field1"
        ]  # both field2 and field3 go to compute
        assert order["form2"] == ["items/field4"]

        assert len(compute["form1"]) == 2
        assert any(
            item["variableName"] == "field2" for item in compute["form1"]
        )
        assert any(
            item["variableName"] == "field3" for item in compute["form1"]
        )


def test_process_csv_missing_columns():
    csv_data = "Column1,Column2\na,b"
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = Path(tmpdir) / "test.csv"
        csv_path.write_text(csv_data)

        with pytest.raises(ValueError):
            process_csv(csv_path, tmpdir, "test_protocol")


def test_normalize_condition():
    # Test calc expressions
    assert (
        normalize_condition("[field1] + [field2]", field_type="calc")
        == "field1 + field2"
    )
    assert (
        normalize_condition("[total]*100", field_type="calc") == "total * 100"
    )
    assert normalize_condition("2+2", field_type="calc") == "2 + 2"

    # Test @CALCTEXT expressions
    assert normalize_condition("3*3") == "3 * 3"

    # Test branching logic
    assert normalize_condition("[age] = 1") == "age == 1"
    assert (
        normalize_condition("[field1] = 1 or [field2] = 2")
        == "field1 == 1 || field2 == 2"
    )
