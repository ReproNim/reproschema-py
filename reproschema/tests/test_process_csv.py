import tempfile
from pathlib import Path

import pytest

from ..convertutils import normalize_condition
from ..redcap2reproschema import process_csv


def test_process_csv():
    csv_data = """Form Name,Variable / Field Name,Field Type,Field Label,Field Annotation,"Choices, Calculations, OR Slider Labels"
form1,field1,text,,,
form1,field2,calc,,,[field1]
form1,field3,text,,@CALCTEXT(3*3),
form2,field4,text,,,
,field5,text,,,"""

    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = Path(tmpdir) / "test.csv"
        csv_path.write_text(csv_data)

        datas, order = process_csv(csv_path)

        assert set(datas.keys()) == {"form1", "form2"}
        assert order == ["form1", "form2"]

        assert datas["form1"]["order"] == [
            "items/field1"
        ]  # both field2 and field3 go to compute
        assert datas["form2"]["order"] == ["items/field4"]

        assert len(datas["form1"]["compute"]) == 2
        assert any(
            item["variableName"] == "field2"
            for item in datas["form1"]["compute"]
        )
        assert any(
            item["variableName"] == "field3"
            for item in datas["form1"]["compute"]
        )


def test_process_csv_missing_columns():
    csv_data = "Column1,Column2\na,b"
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = Path(tmpdir) / "test.csv"
        csv_path.write_text(csv_data)

        with pytest.raises(ValueError):
            process_csv(csv_path)


@pytest.mark.parametrize(
    "condition_str,expected",
    [
        ("[field1] + [field2]", "field1 + field2"),
        ("[total]*100", "total * 100"),
        ("2+2", "2 + 2"),
        ("3*3", "3 * 3"),
        ("[age] = 1", "age == 1"),
        ("[field1] = 1 or [field2] = 2", "field1 == 1 || field2 == 2"),
        ("[age] > 18", "age > 18"),
        ("[some_other_condition] = 1", "some_other_condition == 1"),
        ("[weight] > 0 and [height] > 0", "weight > 0 && height > 0"),
    ],
)
def test_normalize_condition(condition_str, expected):
    # Test calc expressions
    assert normalize_condition(condition_str) == expected
