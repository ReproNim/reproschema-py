![Python package](https://github.com/ReproNim/reproschema-py/actions/workflows/package.yml/badge.svg)

# Reproschema Python library and Command Line Interface (CLI)

The `reproschema-py` library provides a Python interface and a command-line tool to work with ReproSchema, a YAML-based framework for creating and managing reproducible research protocols.

For more information, see the [full documentation](https://ReproNim.github.io/reproschema-py/).

## Installation

reproschema requires Python 3.10+.

```
pip install reproschema
```

## Developer Guide

### Developer installation

Fork this repo to your own GitHub account, then clone and install your forked repo in the developer mode:

```
git clone https://github.com/<your github>/reproschema-py.git
cd reproschema-py
pip install -e .
```
#### Notes on the reproschema model
This repository uses the `pydantic` representation of the `reproschema` model, defined in [model.py](https://github.com/ReproNim/reproschema-py/blob/main/reproschema/models/model.py).
The `pydantic` model is automatically generated from the LinkML model maintained in the [ReproNim/reproschema repository](https://github.com/ReproNim/reproschema).
**All changes to the model should be made in the LinkML source in that repository.**

#### Style
This repo uses pre-commit to check styling.
- Install pre-commit with pip: `pip install pre-commit`
- In order to use it with the repository, you have to run `run pre-commit install` in the root directory the first time you use it.

When pre-commit is used, you may have to run git commit twice,
since pre-commit may make additional changes to your code for styling and will
not commit these changes by default.
