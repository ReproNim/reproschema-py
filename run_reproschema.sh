#!/bin/bash

# Activate micromamba environment for reproschema
eval "$(micromamba shell hook --shell bash)"
micromamba activate reproschema

# Run the command passed as arguments
exec "$@"
