import sys
import os

# Add the parent directory of reproschema to the sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# print(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# sys.path.append('/Users/isaacbevers/sensein/reproschema-wrapper/reproschema-py')


# from reproschema.jsonldutils import load_file, load_directory_structure
# from jsonldutils import load_file

import json


def printj(dict_like_file):
    print(json.dumps(dict_like_file, indent=4, ensure_ascii=False))

def subset_items_dorota(child_activity_path, parent_activity_path):
    """
    Lexically matches the questions in the child activity to
    those in the parent activity. Updates the references in the child
    schema to refer to those in the parent schema. Deletes the overlapping
    items in the child activity.
    """
    child_activity = load_file(child_activity_path)
    # parent_activity = load_file(parent_activity_path)
    return child_activity

def load_items(activity_path):
    items_path = activity_path + "items"
    items = {}
    for filename in os.listdir(items_path):
        # print(filename)
        with open(items_path + "/" + filename, 'r', encoding='utf-8') as file: #replace with load file eventually
            data = json.load(file) 
        items[filename] = data
    return items


def get_question(item_dict):
    if "en" in item_dict["question"]:
        return item_dict["question"]["en"]
    else:
        return item_dict["question"]

def clean_sentence(sentence):
    return ''.join(char.lower() for char in sentence if char.isalnum())

def create_item_mapping(child_activity_path, parent_activity_path):
    child_items = load_items(child_activity_path)
    parent_items = load_items(parent_activity_path)
    item_mapping = {}
    for ckey in child_items:
        child_question = get_question(child_items[ckey])
        for pkey in parent_items:
            parent_question = get_question(parent_items[pkey])
            if clean_sentence(child_question) == clean_sentence(parent_question):
                item_mapping[ckey] = item_mapping[pkey]
    print(item_mapping)
    return item_mapping



    # child_items = []
    # for filename in os.listdir(child_activity_path + "items"):
    #     with open(file_path, 'r', encoding='utf-8') as file: #replace with load file eventually
    #         data = json.load(file)




# def subset_items_old():


# child_activity_path = "/Users/isaacbevers/sensein/reproschema-wrapper/reproschema-library/activities/WHODAS12/items/WHODAS12_4"
# child_activity_path = "/Users/isaacbevers/sensein/reproschema-wrapper/reproschema-library/activities/WHODAS12/"
# parent_activity_path = "/Users/isaacbevers/sensein/reproschema-wrapper/reproschema-library/activities/WHODAS36_S/"
# child_activity_path = "/Users/isaacbevers/sensein/reproschema-wrapper/reproschema-library/activities/dsm_5_parent_guardian_rated_level_1_crosscutting_s/"
child_activity_path = "/Users/isaacbevers/sensein/reproschema-wrapper/reproschema-library/activities/DSM-5_Y/"
parent_activity_path = "/Users/isaacbevers/sensein/reproschema-wrapper/reproschema-library/activities/DSM-5_A/"

create_item_mapping(child_activity_path, parent_activity_path)
# test = subset_items(child_activity_path, parent_activity_path)
# printj(test)


# path = "/Users/isaacbevers/sensein/reproschema-wrapper/reproschema-library/activities/WHODAS36_S/"
# loaded = load_directory_structure(path)
# print(loaded.keys())
