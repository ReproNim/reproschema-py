![Python package](https://github.com/ReproNim/reproschema-py/actions/workflows/package.yml/badge.svg)

# Reproschema Python library and Command Line Interface (CLI)

The `reproschema-py` library provides a Python interface and a command-line tool to work with ReproSchema, a YAML-based framework for creating and managing reproducible research protocols.

For more information, see the [full documentation](https://ReproNim.github.io/reproschema-py/).

## Features

### OpenDataCapture (ODC) to ReproSchema Converter

Convert OpenDataCapture (ODC) form instruments to ReproSchema format with a simple CLI command.

**Supported Conversions:**
- **Simple fields**: string, number, boolean, date
- **Likert scales**: Expanded to multiple individual items
- **Record arrays**: Prefixed sub-items
- **Multiple choice fields**: Single-select and multi-select

## Installation

reproschema requires Python 3.10+.

```
pip install reproschema
```

## Usage

### ODC to ReproSchema Conversion

Convert OpenDataCapture (ODC) form instruments to ReproSchema format:

```bash
# Basic usage
reproschema odc2reproschema input.json

# Specify output directory
reproschema odc2reproschema input.json --output-path ./output

# Specify instrument name
reproschema odc2reproschema input.json --instrument-name "My Assessment"

# Combined options
reproschema odc2reproschema input.json --output-path ./output --instrument-name "My Assessment"
```

**Arguments:**
- `INPUT_FILE`: Path to the ODC JSON instrument file (required)
- `--output-path`, `-o`: Directory to save ReproSchema output (default: current directory)
- `--instrument-name`, `-n`: Name for the ReproSchema activity/protocol (default: uses `internal.name` from ODC file)

**Output Structure:**
```
<output_path>/
└── <instrument_name>/
    ├── <instrument_name>/           # Protocol directory
    │   └── <instrument_name>_schema # Protocol schema
    └── activities/
        └── <instrument_name>/
            ├── <instrument_name>_schema  # Activity schema
            └── items/
                ├── <item1>               # Individual item files
                ├── <item2>
                └── ...
```

**Example:**
```bash
# Convert the sample ODC instrument
reproschema odc2reproschema tests/fixtures/sample_odc_instrument.json --output-path ./output

# Output structure:
# output/
# └── sample_clinical_assessment/
#     ├── sample_clinical_assessment/
#     │   └── sample_clinical_assessment_schema
#     └── activities/
#         └── sample_clinical_assessment/
#             ├── sample_clinical_assessment_schema
#             └── items/
#                 ├── patient_name
#                 ├── age
#                 ├── gender
#                 └── ... (14 total items)
```

### Other ReproSchema CLI Commands

```bash
# Convert CSV to ReproSchema
reproschema csv2reproschema data.csv --output schema.jsonld

# Validate a ReproSchema file
reproschema validate schema.jsonld

# Display protocol information
reproschema info schema.jsonld
```

Run `reproschema --help` for all available commands.

### ODC Field Type Support

| ODC Kind | ODC Variant | ReproSchema Input Type | ReproSchema Value Type |
|----------|-------------|------------------------|------------------------|
| `string` | `input` | `text` | `xsd:string` |
| `string` | `textarea` | `textArea` | `xsd:string` |
| `string` | `password` | `password` | `xsd:string` |
| `number` | `input` | `number` | `xsd:decimal` |
| `number` | `slider` | `range` | `xsd:decimal` |
| `boolean` | `checkbox` | `radio` | `xsd:boolean` |
| `date` | — | `date` | `xsd:date` |
| `set` | `listbox`, `select` | `multiSelect` | `xsd:string` |
| `string` | `radio`, `select` | `radio` | `xsd:string` |
| `record-array` | — | Flattened items | — |
| `number-record` | `likert` | Expanded items | — |

**Special Handling:**
- **Likert scales**: Automatically expanded to multiple individual items (e.g., `satisfaction_likert` → `satisfaction_likert_overall`, `satisfaction_likert_wait_time`)
- **Record arrays**: Nested fieldsets flattened with prefixed item names
- **Multiple choice**: Options converted to ReproSchema response options with proper value types

### Example Output

**Input (ODC JSON):**
```json
{
  "content": {
    "patient_name": {
      "kind": "string",
      "variant": "input",
      "label": "Patient Name",
      "description": "Full name of the patient"
    }
  }
}
```

**Output (ReproSchema item):**
```json
{
  "prefLabel": {"en": "patient_name"},
  "question": {"en": "Patient Name"},
  "description": {"en": "Full name of the patient"},
  "inputType": "text",
  "valueType": "xsd:string"
}
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
