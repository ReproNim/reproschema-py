![Python package](https://github.com/ReproNim/reproschema-py/workflows/Python%20package/badge.svg?branch=master)

# Reproschema Python library and Command Line Interface (CLI)


### Installation

reproschema requires Python 3.7+.

```
pip install reproschema
```

## CLI usage

This package installs `reproschema` a CLI.

```
$ reproschema
Usage: reproschema [OPTIONS] COMMAND [ARGS]...

  A client to support interactions with ReproSchema

  To see help for a specific command, run

  reproschema COMMAND --help     e.g. reproschema validate --help

Options:
  --version
  -l, --log-level [DEBUG|INFO|WARNING|ERROR|CRITICAL]
                                  Log level name  [default: INFO]
  --help                          Show this message and exit.

Commands:
  convert
  create
  serve
  validate
```

## `reproschema2redcap` Usage

### Command-Line Usage

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
  In this case,  the output from `pwd` (which shows your current directory path)should be your `<input_dir_path>`.
- `<output_csv_filename>`: The name of the output CSV file where the converted data will be saved.

### Python Function Usage

You can also use the `reproschema2redcap` function from the `reproschema-py` package in your Python code.

```python
from reproschema import reproschema2redcap

input_dir_path = "path-to/reproschema-demo-protocol"
output_csv_filename = "output.csv"

reproschema2redcap(input_dir_path, output_csv_filename)
```

## Developer installation

Install repo in developer mode:

```
git clone https://github.com/ReproNim/reproschema-py.git
cd reproschema-py
pip install -e .[dev]
```

It is also useful to install pre-commit, which takes care of styling when
committing code. When pre-commit is used you may have to run git commit twice,
since pre-commit may make additional changes to your code for styling and will
not commit these changes by default:

```
pre-commit install
```
