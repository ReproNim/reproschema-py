## Installation

Use the following command to install reproschema:

```
pip install reproschema
```

### Developer installation

Fork this repo to your own GitHub account, then clone and install your forked repo in the developer mode:

```
git clone https://github.com/<your github>/reproschema-py.git
cd reproschema-py
pip install -e .
```
#### Style
This repo uses pre-commit to check styling.
- Install pre-commit with pip: `pip install pre-commit`
- In order to use it with the repository, you have to run `pre-commit install` in the root directory the first time you use it.

When pre-commit is used, you may have to run git commit twice,
since pre-commit may make additional changes to your code for styling and will
not commit these changes by default.
