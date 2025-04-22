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
  reproschema2fhir       Generates FHIR questionnaire resources from reproschema activities
  output2redcap  Generates redcap csv given the audio and survey data from reproschema ui
```
