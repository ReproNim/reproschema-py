# Tests for reproschema-py "models"

## Philosophy

Most of the test are trying to be step by step "recipes" to create the different
files in a schema.

Each test tries to create an item from 'scratch' by using the `Protocol`,
`Activity`, `Item` and `ResponseOptions` classes and writes the resulting
`.jsonld` to the disk.

The file is then read and its content compared to the "expected file" in the
`data` folder.

When testing the Protocol and Activity classes, the output tries to get very
very close to the `jsonld` found in:

```
reproschema/tests/data/activities/items/activity1_total_score
```

Ideally this would avoided having 2 sets of `.jsonld` to test against.

## Running the tests

Requires `pytest` you can `pip install`.

If you are developping the code, also make sure you have installed the
reproschema package locally and not from pypi.

Run this from the root folder of where you cloned the reproschema package:

```
pip install -e .
```

More [here](../../README.md)
