import logging
from datetime import datetime

import pandas as pd
import requests

_LOGGER = logging.getLogger(__name__)


def fetch_json_options_number(raw_url):
    """
    Function to retrieve how many options a specific reproschema item contains.

    Args:
        raw_url: The github raw url to the given reproschema item.
    """
    try:
        # fix url due to the split
        raw_url = raw_url.replace("combined", "questionnaires")
        # Make a GET request to the raw URL
        response = requests.get(raw_url, verify=True)
        response.raise_for_status()  # Raise an error for bad responses (4xx, 5xx)

        # Parse the JSON data
        json_data = response.json()
        return len(json_data["responseOptions"]["choices"])

    except requests.exceptions.RequestException as e:
        _LOGGER.info(f"Error fetching data: {e}")
        return
    except ValueError:
        _LOGGER.info("Error parsing JSON data")


def parse_survey(survey_data, record_id, session_path):
    """
    Function that generates a list of data frames in order to generate a redcap csv
    Args:
        survey_data is the raw json generated from reproschema ui
        record_id is the id that identifies the participant
        session_path is the path containing the session id
    """
    questionnaire_name = survey_data[0]["used"][1].split("/")[-1]
    questions_answers = dict()
    questions_answers["record_id"] = [record_id]
    # questions_answers["redcap_repeat_instrument"] = [questionnaire_name]
    # questions_answers["redcap_repeat_instance"] = [1]
    start_time = survey_data[0]["startedAtTime"]
    end_time = survey_data[0]["endedAtTime"]
    for i in range(len(survey_data)):
        if survey_data[i]["@type"] == "reproschema:Response":
            question = survey_data[i]["isAbout"].split("/")[-1]
            answer = survey_data[i]["value"]
            if not isinstance(answer, list):
                questions_answers[question] = [str(answer).capitalize()]

            else:
                num = fetch_json_options_number(survey_data[i]["isAbout"])

                for options in range(num):
                    if options in answer:
                        questions_answers[f"""{question}___{options}"""] = [
                            "Checked"
                        ]

                    else:
                        questions_answers[f"""{question}___{options}"""] = [
                            "Unchecked"
                        ]

        else:
            end_time = survey_data[i]["endedAtTime"]
    # Adding metadata values for redcap
    questions_answers[f"{questionnaire_name}_start_time"] = [start_time]
    questions_answers[f"{questionnaire_name}_end_time"] = [end_time]

    # Convert the time strings to datetime objects with UTC format
    time_format = "%Y-%m-%dT%H:%M:%S.%fZ"
    start = datetime.strptime(start_time, time_format)
    end = datetime.strptime(end_time, time_format)
    duration = end - start
    # convert to milliseconds
    duration = duration.microseconds // 1000

    questions_answers[f"{questionnaire_name}_duration"] = [duration]

    df = pd.DataFrame(questions_answers)
    return [df]
