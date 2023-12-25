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

## redcap2reproschema.py Usage

### Prerequisites
Before using the conversion script, ensure you have the following:

1. **GitHub Repository**: 
   - [Create a GitHub repository](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-new-repository) named `reproschema` to store all your reproschema protocols. 
   - This repository should be set up before converting any data using the script.

2. **YAML Configuration File**:
   - Fill out the `templates/redcap2rs.yaml` file with your protocol details.

### YAML File Configuration
In the `templates/redcap2rs.yaml` file, provide the following information:

- **protocol_name**: This is a unique identifier for your protocol. Use underscores for spaces and avoid special characters.
- **protocol_display_name**: The name that will appear in the application.
- **user_name**: Your GitHub username.
- **repo_name**: The repository name where your protocols are stored. It's recommended to use `reproschema`.
- **protocol_description**: A brief description of your protocol.

Example:
```yaml
protocol_name: "My_Protocol"
protocol_display_name: "Assessment Protocol"
user_name: "john_doe"
repo_name: "reproschema"
protocol_description: "This protocol is for assessing cognitive skills."
```

### Using the Script

After configuring the YAML file:

1. Run the Python script with the paths to your CSV file and the YAML file as arguments.
2. Command Format: `python script_name.py path/to/your_redcap_data_dic.csv path/to/your_redcap2rs.yaml`

### Notes
1. The script requires an active internet connection to access the GitHub repository.
2. Make sure you use `git add`, `git commit`, `git push` properly afterwards to maintain a good version control for your converted data.

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
