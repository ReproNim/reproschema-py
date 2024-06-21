![Python package](https://github.com/ReproNim/reproschema-py/actions/workflows/package.yml/badge.svg)

# Reproschema Python library and Command Line Interface (CLI)

## Installation

reproschema requires Python 3.10+.

```
pip install reproschema
```

### Developer installation

After you create a fork, you can clone and install repo in developer mode:

```
git clone https://github.com/<your github>/reproschema-py.git
cd reproschema-py
pip install -e .[dev]
```
#### Style
This repo uses pre-commit to check styling.
- Install pre-commit with pip: `pip install pre-commit`
- In order to use it with the repository, you have to run `run pre-commit install` in the root directory the first time you use it.

When pre-commit is used you may have to run git commit twice,
since pre-commit may make additional changes to your code for styling and will
not commit these changes by default.


## CLI usage

This package installs `reproschema` Command Line Interface (CLI).

```
$ reproschema --help

$  A client to support interactions with ReproSchema

  To see help for a specific command, run

  reproschema COMMAND --help     e.g. reproschema validate --help

Options:
  --version
  -l, --log-level [DEBUG|INFO|WARNING|ERROR|CRITICAL]
                                  Log level name  [default: INFO]
  --help                          Show this message and exit.

Commands:
  convert             Converts a path to a different format, jsonld,...
  create
  migrate             Updates to a new reproschema version
  redcap2reproschema  Converts REDCap CSV files to Reproschema format.
  reproschema2redcap  Converts reproschema protocol to REDCap CSV format.
  serve
  validate            Validates if the path has a valid reproschema format
```

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

## `redcap2reproschema`
The `redcap2reproschema` function is designed to process a given REDCap CSV file and YAML configuration to generate the output in the reproschema format.

### Prerequisites
Before the conversion, ensure you have the following:

**YAML Configuration File**:
   - Download [templates/redcap2rs.yaml](templates/redcap2rs.yaml) and fill it out with your protocol details.

### YAML File Configuration
In the `templates/redcap2rs.yaml` file, provide the following information:

- **protocol_name**: This is a unique identifier for your protocol. Use underscores for spaces and avoid special characters.
- **protocol_display_name**: The name that will appear in the application.
- **protocol_description**: A brief description of your protocol.

Example:
```yaml
protocol_name: "My_Protocol"
protocol_display_name: "Assessment Protocol"
protocol_description: "This protocol is for assessing cognitive skills."
```
### CLI Usage

The `redcap2reproschema`` function has been integrated into a CLI tool, use the following command:
```bash
reproschema redcap2reproschema path/to/your_redcap_data_dic.csv path/to/your_redcap2rs.yaml
```

Optionally you can provide a path to the output directory (defaults is the current directory) by adding option: `--output-path PATH`
### Python Function Usage

You can also use the `redcap2reproschema` function from the `reproschema-py` package in your Python code.

```python
from reproschema import redcap2reproschema

csv_path = "path-to/your_redcap_data_dic.csv"
yaml_path = "path-to/your_redcap2rs.yaml"
output_path = "path-to/directory_you_want_to_save_output"

reproschema2redcap(csv_file, yaml_file, output_path)
```

### Notes
1. The script requires an active internet connection to access the GitHub repository.
