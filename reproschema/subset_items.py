import sys
import os

# Add the parent directory of reproschema to the sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# print(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# sys.path.append('/Users/isaacbevers/sensein/reproschema-wrapper/reproschema-py')


from reproschema.jsonldutils import load_file, load_directory_structure

# from jsonldutils import load_file

import json


def printj(dict_like_file):
    print(json.dumps(dict_like_file, indent=4, ensure_ascii=False))


def subset_items(child_activity_path, parent_activity_path):
    """
    Lexically matches the questions in the child activity to
    those in the parent activity. Updates the references in the child
    schema to refer to those in the parent schema. Deletes the overlapping
    items in the child activity.
    """
    child_activity = load_file(child_activity_path)
    # parent_activity = load_file(parent_activity_path)
    return child_activity


# child_activity_path = "/Users/isaacbevers/sensein/reproschema-wrapper/reproschema-library/activities/WHODAS12/items/WHODAS12_4"
# # child_activity_path = "/Users/isaacbevers/sensein/reproschema-wrapper/reproschema-library/activities/WHODAS12/"
# parent_activity_path = "/Users/isaacbevers/sensein/reproschema-wrapper/reproschema-library/activities/WHODAS36_S/"
# test = subset_items(child_activity_path, parent_activity_path)
# printj(test)


path = "/Users/isaacbevers/sensein/reproschema-wrapper/reproschema-library/activities/WHODAS36_S/"
loaded = load_directory_structure(path)
print(loaded.keys())
