## `redcap2reproschema`
The `redcap2reproschema` function is designed to process a given REDCap CSV file and YAML configuration to generate the output in the reproschema format.

### Prerequisites
Before the conversion, ensure you have the following:

**YAML Configuration File**:
   - Download [templates/redcap2rs.yaml](templates/redcap2rs.yaml) and fill it out with your protocol details.

### YAML File Configuration
In the `templates/redcap2rs.yaml` file, provide the following information:

- **protocol_name**: A unique identifier for your protocol. Use underscores for spaces and avoid special characters.
- **protocol_display_name**: Name that will appear in the application.
- **protocol_description**: A brief description of your protocol.
- **redcap_version**: Version of your redcap file (you can customize it).

Example:
```yaml
protocol_name: "My_Protocol"
protocol_display_name: "Assessment Protocol"
protocol_description: "This protocol is for assessing cognitive skills."
redcap_version: "X.XX.X"
```
### CLI Usage

The `redcap2reproschema` function has been integrated into a CLI tool, use the following command:
```bash
reproschema redcap2reproschema path/to/your_redcap_data_dic.csv path/to/your_redcap2rs.yaml
```

Optionally you can provide a path to the output directory (default is the current directory) by adding the option: `--output-path PATH`
### Python Function Usage

You can also use the `redcap2reproschema` function from the `reproschema-py` package in your Python code.

```python
from reproschema import redcap2reproschema

csv_path = "path-to/your_redcap_data_dic.csv"
yaml_path = "path-to/your_redcap2rs.yaml"
output_path = "path-to/directory_you_want_to_save_output"

redcap2reproschema(csv_file, yaml_file, output_path)
```
