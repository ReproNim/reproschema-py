import csv
import os
from pathlib import Path
from shutil import copytree, rmtree

import pytest
from click.testing import CliRunner

from ..cli import main
from ..context_url import CONTEXTFILE_URL
from ..jsonldutils import _is_url, load_file
from ..models import Activity, Item, Protocol, ResponseOption
from ..redcap2reproschema import normalize_condition
from ..utils import fixing_old_schema, start_server, stop_server


def create_protocol_dict(
    protocol_schema,
    contextfile=CONTEXTFILE_URL,
    started=False,
    http_kwargs=None,
):
    """creating dictionary with objects to compare"""
    protocol_dir = Path(protocol_schema).parent
    prot_tree_dict = {}
    protocol_data = load_file(
        protocol_schema,
        started=started,
        http_kwargs=http_kwargs,
        fixoldschema=True,
        compact=True,
        compact_context=contextfile,
    )
    # obj_type = identify_model_class(data["@type"][0])
    del protocol_data["@context"]
    prot = Protocol(**protocol_data)
    prot_tree_dict["obj"] = prot
    prot_tree_dict["activities"] = {}

    activity_order = prot.ui.order
    for activity_path in activity_order:
        if not _is_url(activity_path):
            activity_path = protocol_dir / activity_path
        parsed_activity_json = load_file(
            activity_path,
            started=started,
            http_kwargs=http_kwargs,
            fixoldschema=True,
            compact=True,
            compact_context=contextfile,
        )
        del parsed_activity_json["@context"]
        act = Activity(**parsed_activity_json)
        act_name = act.id.split("/")[-1].split(".")[0]
        prot_tree_dict["activities"][act_name] = {"obj": act, "items": {}}

        item_order = act.ui.order
        for item in item_order:
            if not _is_url(item):
                item = activity_path.parent / item
            item_json = load_file(
                item,
                started=started,
                http_kwargs=http_kwargs,
                fixoldschema=True,
                compact=True,
                compact_context=contextfile,
            )

            item_json.pop("@context", "")
            itm = Item(**item_json)
            if isinstance(itm.responseOptions, str):
                resp = load_file(
                    itm.responseOptions,
                    started=started,
                    http_kwargs=http_kwargs,
                    fixoldschema=True,
                    compact=True,
                    compact_context=contextfile,
                )
                del resp["@context"]
                itm.responseOptions = ResponseOption(**resp)
            itm_name = itm.id.split("/")[-1].split(".")[0]
            prot_tree_dict["activities"][act_name]["items"][itm_name] = {
                "obj": itm
            }

    return prot_tree_dict


def errors_check(cat, atr, orig, final):
    # orig = orig.strip() if orig else orig
    # final = final.strip() if final else final
    if (orig and final and orig == final) or (not orig and not final):
        return None
    if orig and not final:
        print(f"Attribute {atr} is missing in the final {cat}")
    elif not orig and final:
        print(f"Attribute {atr} is missing in the original {cat}")
    elif orig != final:
        print(f"Attribute {atr} is different in the final {cat}")
        print(f"Original: {orig}")
        print(f"Final: {final}")
    error_shortmsg = f"{cat}: {atr} is different"
    return error_shortmsg


def print_return_msg(error_msg):
    print(error_msg)
    return error_msg


def compare_protocols(prot_tree_orig, prot_tree_final):
    # compare the two dictionaries
    errors_list = []
    warnings_list = []
    # comparing protocols
    prot_orig = prot_tree_orig["obj"]
    prot_final = prot_tree_final["obj"]
    for atr in ["description", "prefLabel"]:
        error_shortmsg = errors_check(
            "Protocol", atr, getattr(prot_orig, atr), getattr(prot_final, atr)
        )
        if error_shortmsg:
            errors_list.append(error_shortmsg)
    # checking orders, ignoring some variability in the names syntax
    order_orig = [
        el.split("/")[-1].split(".")[0].replace("_schema", "")
        for el in prot_orig.ui.order
    ]
    order_final = [
        el.split("/")[-1].split(".")[0].replace("_schema", "")
        for el in prot_final.ui.order
    ]
    error_shortmsg = errors_check("Protocol", "order", order_orig, order_final)
    if error_shortmsg:
        errors_list.append(error_shortmsg)

    # comparing activities
    for act_name in prot_tree_orig["activities"]:
        act_orig = prot_tree_orig["activities"][act_name]["obj"]
        act_items_orig = prot_tree_orig["activities"][act_name]["items"]
        if act_name in prot_tree_final["activities"]:
            act_final = prot_tree_final["activities"][act_name]["obj"]
            act_items_final = prot_tree_final["activities"][act_name]["items"]
        # inconsistent naming in the schema suffixes
        elif f"{act_name}_schema" in prot_tree_final["activities"]:
            act_final = prot_tree_final["activities"][f"{act_name}_schema"][
                "obj"
            ]
            act_items_final = prot_tree_final["activities"][
                f"{act_name}_schema"
            ]["items"]
        else:
            errors_list.append(
                print_return_msg(f"Activity {act_name} is missing")
            )
            continue

        # check preamble
        preamble_orig = getattr(act_orig, "preamble", {}).get("en", "").strip()
        preamble_final = (
            getattr(act_final, "preamble", {}).get("en", "").strip()
        )
        error_shortmsg = errors_check(
            f"Activity {act_name}", "preamble", preamble_orig, preamble_final
        )
        if error_shortmsg:
            errors_list.append(error_shortmsg)
        # checking id (if there is just a different in the _schema part, do not add to the errors)
        acd_orig_id = act_orig.id.split("/")[-1].split(".")[0]
        acd_final_id = act_final.id.split("/")[-1].split(".")[0]
        error_shortmsg = errors_check(
            f"Activity {act_name}", "id", acd_orig_id, acd_final_id
        )
        if error_shortmsg:
            if errors_check(
                f"Activity {act_name}",
                "id",
                acd_orig_id.replace("_schema", ""),
                acd_final_id.replace("_schema", ""),
            ):
                errors_list.append(error_shortmsg)
            else:  # differences only in the "_schema suffix
                warnings_list.append(error_shortmsg)

        # check order
        act_order_orig = [
            el.split("/")[-1].split(".")[0] for el in act_orig.ui.order
        ]
        act_order_final = [
            el.split("/")[-1].split(".")[0] for el in act_final.ui.order
        ]
        error_shortmsg = errors_check(
            f"Activity {act_name}", "order", act_order_orig, act_order_final
        )
        if error_shortmsg:
            errors_list.append(error_shortmsg)

        # check addproperties
        act_props_orig = {
            el.variableName: el for el in act_orig.ui.addProperties
        }
        act_props_final = {
            el.variableName: el for el in act_final.ui.addProperties
        }
        # issues with these schema reprorted in the reproschema-library
        known_issues_nm = [
            "dsm_5_parent_guardian_rated_level_1_crosscutting_s_schema_first_19",
            "dsm_5_parent_guardian_rated_level_1_crosscutting_s_schema_20_to_25",
            "RCADS25_caregiver_administered_schema",
            "RCADS25_youth_administered_schema",
            "DSM5_crosscutting_youth_schema",
        ]
        if act_props_orig.keys() != act_props_final.keys():
            if act_name in known_issues_nm:
                warnings_list.append(
                    print_return_msg(
                        f"Activity {act_name}: addProperties have different elements"
                    )
                )
            else:
                print(
                    f"Activity {act_name}: addProperties have different elements"
                )
                errors_list.append(
                    f"Activity {act_name}: addProperties have different elements"
                )
        else:
            for nm, el in act_props_final.items():
                for key in ["isVis", "valueRequired"]:
                    error = False
                    if (getattr(act_props_orig[nm], key) is not None) and (
                        normalize_condition(getattr(el, key))
                        != normalize_condition(
                            getattr(act_props_orig[nm], key)
                        )
                    ):
                        error = True
                    elif (
                        getattr(el, key)
                        and getattr(act_props_orig[nm], key) is None
                    ):
                        if (
                            key == "isVis"
                            and normalize_condition(getattr(el, key)) != True
                        ):
                            error = True
                        elif (
                            key == "valueRequired"
                            and normalize_condition(getattr(el, key)) != False
                        ):
                            error = True
                    if error:
                        errors_list.append(
                            print(
                                f"Activity {act_name}: addProperties {nm} have different {key}"
                            )
                        )
        # check compute
        act_comp_orig = {el.variableName: el for el in act_orig.compute}
        act_comp_final = {el.variableName: el for el in act_final.compute}
        if act_comp_final.keys() != act_comp_orig.keys():
            if act_name in known_issues_nm:
                warnings_list.append(
                    print_return_msg(
                        f"Activity {act_name}: compute have different elements"
                    )
                )
            else:
                print(f"Activity {act_name}: compute have different elements")
                errors_list.append(
                    f"Activity {act_name}: compute have different elements"
                )
        else:
            for nm, el in act_comp_final.items():
                if normalize_condition(
                    getattr(el, "jsExpression")
                ) != normalize_condition(
                    getattr(act_comp_orig[nm], "jsExpression")
                ):
                    errors_list.append(
                        print(
                            f"Activity {act_name}: compute {nm} have different jsExpression"
                        )
                    )

        # check items:
        if act_items_final.keys() != act_items_orig.keys():
            if act_name in known_issues_nm:
                warnings_list.append(
                    print_return_msg(
                        f"Activity {act_name}: items have different elements"
                    )
                )
            else:
                errors_list.append(
                    print_return_msg(
                        f"Activity {act_name}: items have different elements"
                    )
                )
        else:
            for nm, el in act_items_final.items():
                if (
                    el["obj"].id.split("/")[-1].split(".")[0]
                    != act_items_orig[nm]["obj"]
                    .id.split("/")[-1]
                    .split(".")[0]
                ):
                    errors_list.append(
                        print_return_msg(
                            f"Activity {act_name}: items {nm} have different id"
                        )
                    )
                elif normalize_condition(
                    el["obj"].question.get("en", "")
                ) != normalize_condition(
                    act_items_orig[nm]["obj"].question.get("en", "")
                ):
                    if "<br><br>" in normalize_condition(
                        act_items_orig[nm]["obj"].question.get("en", "")
                    ):
                        warnings_list.append(
                            print_return_msg(
                                f"Activity {act_name}: items {nm} have different question, FIX normalized function!!!"
                            )
                        )
                    else:
                        errors_list.append(
                            print_return_msg(
                                f"Activity {act_name}: items {nm} have different question"
                            )
                        )
                elif (
                    el["obj"].ui.inputType
                    != act_items_orig[nm]["obj"].ui.inputType
                ):
                    if act_items_orig[nm]["obj"].ui.inputType in [
                        "save",
                        "static",
                    ]:
                        warnings_list.append(
                            print_return_msg(
                                f"Activity {act_name}: items {nm} have different inputType, "
                                f"we dont have representation of {el['obj'].ui.inputType}"
                            )
                        )
                    else:
                        errors_list.append(
                            print_return_msg(
                                f"Activity {act_name}: items {nm} have different inputType"
                            )
                        )
                # check response options
                respopt_orig = act_items_orig[nm]["obj"].responseOptions
                respopt_final = el["obj"].responseOptions
                # TODO: min val does not work
                # TODO: check choices
                # for key in ["minValue", "maxValue"]:
                #     if getattr(respopt_final, key) != getattr(respopt_orig, key):
                #         errors_list.append(print(f"Activity {act_name}: items {nm} have different {key}"))
    return errors_list, warnings_list


def test_rs2redcap_redcap2rs(tmpdir):
    runner = CliRunner()
    copytree(
        Path(__file__).parent / "data_test_nimh-minimal",
        tmpdir / "nimh_minimal_orig",
    )
    tmpdir.chdir()
    print("\n current dir", os.getcwd())
    result1 = runner.invoke(
        main,
        [
            "reproschema2redcap",
            "nimh_minimal_orig/nimh_minimal",
            "output_nimh.csv",
        ],
    )
    print("\n results of reproschema2redcap", result1.output)

    result2 = runner.invoke(
        main,
        [
            "redcap2reproschema",
            "output_nimh.csv",
            "nimh_minimal_orig/test_nimh-minimal.yaml",
            "--output-path",
            "output_nimh",
        ],
    )

    print("\n results of redcap2reproschema", result2.output)

    protocol_schema_orig = (
        "nimh_minimal_orig/nimh_minimal/nimh_minimal/nimh_minimal_schema"
    )
    protocol_schema_final = (
        "output_nimh/nimh_minimal/nimh_minimal/nimh_minimal_schema"
    )

    http_kwargs = {}
    stop, port = start_server()
    http_kwargs["port"] = port

    try:
        prot_tree_orig = create_protocol_dict(
            protocol_schema_orig, started=True, http_kwargs=http_kwargs
        )
        prot_tree_final = create_protocol_dict(
            protocol_schema_final, started=True, http_kwargs=http_kwargs
        )
    except:
        raise
    finally:
        stop_server(stop)

    errors_list, warnings_list = compare_protocols(
        prot_tree_orig, prot_tree_final
    )

    assert not errors_list, f"Errors: {errors_list}"
    print("No errors, but found warnings: ", warnings_list)
