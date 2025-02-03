import tempfile
from pathlib import Path

import pandas as pd
import pytest

from ..redcap2reproschema import process_csv


def test_process_csv():
    csv_data = """Form Name,Variable / Field Name,Field Type,Field Annotation,Choices Calculations OR Slider Labels
form1,field1,text,,
form1,field2,calc,,2+2
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

        assert order["form1"] == ["items/field1"]  # field3 goes to compute
        assert order["form2"] == ["items/field4"]

        assert len(compute["form1"]) == 2
        assert compute["form1"][0]["variableName"] == "field2"
        assert compute["form1"][1]["variableName"] == "field3"


def test_process_csv_missing_columns():
    csv_data = "Column1,Column2\na,b"
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = Path(tmpdir) / "test.csv"
        csv_path.write_text(csv_data)

        with pytest.raises(ValueError):
            process_csv(csv_path, tmpdir, "test_protocol")
