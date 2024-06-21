import json
import os
import shutil
from pathlib import Path

from .jsonldutils import load_file
from .utils import fixing_old_schema


def migrate2newschema(path, inplace=False, fixed_path=None):
    path = Path(path).resolve()
    if path.is_file():
        print(f"migration of file: {path}")
        new_path = migrate2newschema_file(path, inplace, fixed_path)
    else:  # path.is_dir
        if inplace:
            new_path = path
        elif fixed_path:
            new_path = Path(fixed_path).resolve()
            shutil.copytree(path, new_path)
        else:
            new_path = path.parent / f"{path.name}_after_migration"
            shutil.copytree(path, new_path)
        # fixing all files in new_path
        all_files = Path(new_path).rglob("*")
        for file in all_files:
            if file.is_file():
                migrate2newschema_file(jsonld_path=file, inplace=True)
    return new_path


def migrate2newschema_file(jsonld_path, inplace=False, fixed_path=None):
    print(f"Fixing {jsonld_path}")
    data = load_file(jsonld_path, started=False)
    data_fixed = [fixing_old_schema(data, copy_data=True)]
    if inplace:
        new_filename = jsonld_path
    elif fixedjsonld_path:
        new_filename = fixed_path
    else:
        root, ext = os.path.splitext(jsonld_path)
        new_filename = f"{root}_after_migration{ext}"
    with open(new_filename, "w") as f:
        json.dump(data_fixed, f, indent=4)
    return new_filename
