# LORIS to ReproSchema Conversion

The `reproschema loris2reproschema` command converts a LORIS data dictionary in CSV format to the ReproSchema format.

## Usage

```bash
reproschema loris2reproschema [OPTIONS] CSV_FILE CONFIG_FILE
```

### Arguments

- `CSV_FILE`: Path to the LORIS data dictionary CSV file. (Required)
- `CONFIG_FILE`: Path to the YAML configuration file. (Required)

### Options

- `--output-path PATH`: Path to the output directory. Defaults to the current directory.
- `--encoding TEXT`: Encoding to use for reading the CSV file (e.g., `utf-8`, `latin-1`).
- `--analyze`: Only analyze the CSV file structure and exit without conversion.
- `--verbose`: Enable verbose logging.
- `--help`: Show the help message and exit.

## Configuration File

The conversion process is controlled by a YAML configuration file. This file specifies how to map the columns in your LORIS CSV to ReproSchema fields, and provides metadata for the protocol.

Here is an example of a configuration file:

```yaml
# Protocol information
protocol_name: "HBCD_LORIS"
protocol_display_name: "HEALthy Brain and Child Development Study"
protocol_description: "Protocol for the HBCD study using LORIS data dictionary"
loris_version: "1.0.0"

# Column mappings from LORIS CSV to ReproSchema
column_mappings:
  activity_name: "full_instrument_name"
  item_name: "name"
  question: "question"
  field_type: "field_type"
  response_option_labels: "option_labels"
  response_option_values: "option_values"
```

## Example

To convert a LORIS CSV file named `HBCD_LORIS.csv` using a configuration file `hbcd-loris.yml`, you would run:

```bash
reproschema loris2reproschema HBCD_LORIS.csv hbcd-loris.yml --output-path my-protocol
```

This will create a new directory named `my-protocol/HBCD_LORIS` containing the ReproSchema representation of your protocol.
