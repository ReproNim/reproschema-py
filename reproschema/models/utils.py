from collections import OrderedDict
from typing import Dict
from typing import List


def reorder_dict_skip_missing(old_dict: Dict, key_list: List) -> OrderedDict:
    """
    reorders dictionary according to ``key_list``
    removing any key with no associated value
    or that is not in the key list
    """
    return OrderedDict(
        (k, old_dict[k])
        for k in key_list
        if (k in old_dict and old_dict[k] not in ["", [], None])
    )
