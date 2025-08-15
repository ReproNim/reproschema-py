# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ReproSchema Python library and CLI for working with ReproSchema format - a standardized way to represent assessments, questionnaires, and protocols used in research. The library provides validation, conversion utilities, and integrations with REDCap and FHIR.

## Key Commands

### Development Setup
```bash
# Install in development mode
pip install -e .

# Install with all development dependencies  
pip install -e ".[dev]"

# Run pre-commit hooks
pre-commit install
pre-commit run --all-files
```

### Testing
```bash
# Run tests with coverage
pytest --cov=reproschema

# Run specific test file
pytest reproschema/tests/test_validate.py

# Run tests in parallel
pytest -n auto
```

### Linting and Formatting
```bash
# Format code with black
black reproschema/

# Run flake8 linter
flake8 reproschema/

# Sort imports
isort reproschema/

# Check spelling
codespell
```

## Architecture

### Core Modules

- **reproschema/cli.py**: Main CLI entry point using Click framework. Provides commands for validation, conversion, migration.
- **reproschema/models/model.py**: Pydantic models auto-generated from LinkML schema. DO NOT modify directly - changes should be made in ReproNim/reproschema repository.
- **reproschema/validate.py**: Schema validation using PyShacl
- **reproschema/redcap2reproschema.py**: Convert REDCap CSV to ReproSchema format
- **reproschema/reproschema2redcap.py**: Convert ReproSchema to REDCap CSV format  
- **reproschema/reproschema2fhir.py**: Convert ReproSchema to FHIR Questionnaire resources
- **reproschema/output2redcap.py**: Process reproschema-ui output into REDCap CSV

### Conversion Workflows

1. **REDCap → ReproSchema**: Requires CSV data dictionary + YAML config file
2. **ReproSchema → REDCap**: Takes protocol directory, outputs CSV
3. **ReproSchema → FHIR**: Converts activities/items to FHIR Questionnaire
4. **UI Output → REDCap**: Processes survey responses to REDCap format

## CLI Commands

- `reproschema validate <path>` - Validate ReproSchema format
- `reproschema redcap2reproschema <csv> <yaml>` - Convert REDCap to ReproSchema
- `reproschema reproschema2redcap <input_dir> <output_csv>` - Convert ReproSchema to REDCap
- `reproschema reproschema2fhir <input_dir> <output_dir>` - Convert to FHIR
- `reproschema output2redcap <input_dir> <output_dir>` - Process UI output
- `reproschema migrate <path>` - Migrate to new schema version
- `reproschema convert` - Convert between formats (jsonld, n-triples, turtle)

## Important Notes

- Python 3.10+ required
- The Pydantic models in `reproschema/models/model.py` are auto-generated - DO NOT edit directly
- All schema changes must be made in the LinkML source at ReproNim/reproschema repository
- Uses pre-commit for code quality - commits may require running twice
- Line length limit: 79 characters (enforced by black)