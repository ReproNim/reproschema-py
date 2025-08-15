## `reproschema2redcap`

### CLI Usage

You can use this feature directly from the command line. To convert ReproSchema protocol to REDCap CSV format, use the following command

```
reproschema reproschema2redcap <input_dir_path> <output_csv_filename>
```

- `<input_dir_path>`: The path to the root folder of a protocol. For example, to convert the reproschema-demo-protocol provided by ReproNim, you can use the following commands:
  ```bash
  git clone https://github.com/ReproNim/reproschema-demo-protocol.git
  cd reproschema-demo-protocol
  pwd
  ```
  In this case,  the output from `pwd` (which shows your current directory path) should be your `<input_dir_path>`.
- `<output_csv_filename>`: The name of the output CSV file where the converted data will be saved.

### Python Function Usage

You can also use the `reproschema2redcap` function from the `reproschema-py` package in your Python code.

```python
from reproschema import reproschema2redcap

input_dir_path = "path-to/reproschema-demo-protocol"
output_csv_filename = "output.csv"

reproschema2redcap(input_dir_path, output_csv_filename)
```
