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
