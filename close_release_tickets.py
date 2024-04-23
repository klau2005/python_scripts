""" Close all Jira tickets related to an release

The script is smart as it will keep a JSON file with all Jira projects,
ticket types and statuses so it will know what counts as Closed status
(different teams use different workflows with different names for the
Done/Closed status). The way it works is by initially prompting the
user for the correct closed status and learn it so that next time it
will come across a ticket form the same project and with the same
type, it will know what to do without user action.
"""

__version__ = "0.1"
__date__ = "October 2019"
__author__ = "Claudiu Tomescu"
__email__ = "klau2005@tutanota.com"

import argparse
import json
import logging
import requests
import sys
from datetime import datetime as dt
from atlassian import Bitbucket, Jira

# logging config - NEEDS work!
logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)
fh = logging.StreamHandler()
logger.addHandler(fh)

parser = argparse.ArgumentParser(
    description="Close the Jira tickets related to a release"
    )
parser.add_argument(
    "-w", "--week", help="Specify week number", type=int, required=True
    )
parser.add_argument(
    "-y", "--year", help="Specify year (4 digits), defaults to current one",
    type=int
    )
parser.add_argument(
    "-t", "--test",
    help="Useful this if you need to find out the actions about to be applied",
    type=bool, default=False
    )
args = parser.parse_args()

jira_statuses_file = "jira_statuses.json"
# get current year number
iso_date = dt.isocalendar(dt.now())
curr_year = str(iso_date[0])
curr_year_short = curr_year[2:]

# make sure week number is always 2 digits (with leading zero where necessary)
week_number = "{:02d}".format(args.week)
year = args.year
if (year and len(year) != 4):
    logger.error(
        "Please specify year as a 4 digits number to prevent ambiguity"
        )
    sys.exit(1)
elif year:
    year = str(year)[2:]
else:
    year = curr_year_short

test_mode = args.test

jira_url = "https://jira.example.com"
# TODO - create dedicated API user for BB/Confluence/Jira
user = "<username>"
passwd = "<password>"

# dirty check to validate user credentials
if (user == "<username>" or passwd == "<password>"):
    logger.info("Oops, did you forget to change the username/password?\nExiting now...")
    sys.exit(1)

operator_major_version = 4
operator_version = "Operator {0}.{1}.{2}".format(
    operator_major_version, year, week_number
    )

jql = 'fixVersion = "{0}"'.format(operator_version)


def get_closed_status(jira_ticket, ticket_status):
    """Return Closed/Done status for a ticket (or None if not known)."""
    while True:
        final_status = input(
            "Is status '{0}' of ticket '{1}' considered as CLOSED? (Yes/No)\n"
            .format(ticket_status, jira_ticket)
            )
        final_status = final_status.lower()
        if final_status in ["yes", "no"]:
            break
    return ticket_status if final_status == "yes" else None


def get_transitions(jira_conn, jira_ticket, ticket_status):
    """Get available transitions for a Jira ticket."""
    transitions_result = jira_conn.get_issue_transitions(jira_ticket)
    print("Current status for ticket '{0}': '{1}'".format(
        jira_ticket, ticket_status
        )
        )
    if len(transitions_result) == 0:
        print("No available transition!")
        return (None, None)
    else:
        print("Available transitions:")
        for transition in transitions_result:
            print("{0}. '{1}' to status '{2}'".format(
                transitions_result.index(transition) + 1,
                transition["name"],
                transition["to"]
                )
                )
        transition = input(
            "Choose the transition to perform for moving the ticket to\n\
            CLOSED/DONE status (0 if none of the above):\n"
            )
        transition = int(transition)
        if transition == 0:
            return (None, None)
        else:
            return (
                transitions_result[transition - 1]["to"],
                transitions_result[transition - 1]["id"]
                )


def get_value(key):
    """Return value of a nested dictionary key"""
    return statuses_json[project_key][ticket_type][key]


def main():
    if test_mode:
        # TODO - implement proper test mode
        print("Test mode not implemented yet!")
        sys.exit(0)
    # initiate the Jira connection
    jira = Jira(
        url=jira_url,
        username=user,
        password=passwd
        )

    # load the json file in memory
    try:
        with open(jira_statuses_file, "r") as f:
            statuses_file = f.read()
    except FileNotFoundError:
        statuses_json = {}
    else:
        try:
            statuses_json = json.loads(statuses_file)
        except json.decoder.JSONDecodeError:
            # either the file does not exist yet or it has an incorrect
            # format so we reset it
            statuses_json = {}
    # run the JQL query to get the list of Jira tickets for the
    # Operator version we are processing
    result = jira.jql(
        jql, fields='status,issuetype,project', limit=500, expand=None
        )
    try:
        jira_list = result["issues"]
    except TypeError:
        print("Received not expected result, exiting...")
        sys.exit(1)
    # parse the JIRA tickets list
    for item in jira_list:
        project_keys_list = list(statuses_json.keys())
        project_key = item["fields"]["project"]["key"]
        ticket_type = item["fields"]["issuetype"]["name"]
        jira_ticket = item["key"]
        ticket_status = item["fields"]["status"]["name"]
        # check if the ticket project is present in the JSON
        if project_key not in project_keys_list:
            transitions = get_transitions(jira, jira_ticket, ticket_status)
            transition_to = transitions[0]
            transition_id = transitions[1]
            if transition_id is None:
                statuses_json[project_key] = {
                    ticket_type: {
                        "closed_status": get_closed_status(
                            jira_ticket, ticket_status
                            ),
                        "to_status": transition_to,
                        "transition_id": transition_id
                        }
                    }
            else:
                print("Transitioning ticket '{0}' to '{1}' status..."
                      .format(jira_ticket, transition_to))
                jira.set_issue_status_by_transition_id(
                    jira_ticket, transition_id
                    )
                statuses_json[project_key] = {
                    ticket_type: {
                        "closed_status": transition_to,
                        "to_status": transition_to,
                        "transition_id": transition_id
                        }
                    }
            if get_value("closed_status") is None:
                print(
                    "Ticket '{0}' is not in the correct status, please check."
                    .format(jira_ticket)
                    )
        elif ticket_type not in statuses_json[project_key].keys():
            transitions = get_transitions(jira, jira_ticket, ticket_status)
            transition_to = transitions[0]
            transition_id = transitions[1]
            if transition_id is None:
                statuses_json[project_key][ticket_type] = {
                    "closed_status": get_closed_status(
                        jira_ticket, ticket_status
                        ),
                    "to_status": transition_to,
                    "transition_id": transition_id
                    }
            else:
                print("Transitioning ticket '{0}' to '{1}' status..."
                      .format(jira_ticket, transition_to))
                jira.set_issue_status_by_transition_id(
                    jira_ticket, transition_id
                    )
                statuses_json[project_key][ticket_type] = {
                    "closed_status": transition_to,
                    "to_status": transition_to,
                    "transition_id": transition_id
                    }
            if get_value("closed_status") is None:
                print(
                    "Ticket '{0}' is not in the correct status, please check."
                    .format(jira_ticket)
                    )
        elif get_value("closed_status") is None:
            transitions = get_transitions(jira, jira_ticket, ticket_status)
            transition_to = transitions[0]
            transition_id = transitions[1]
            if transition_id is None:
                statuses_json[project_key][ticket_type] = {
                    "closed_status": get_closed_status(
                        jira_ticket, ticket_status
                        ),
                    "to_status": transition_to,
                    "transition_id": transition_id
                    }
            else:
                print(
                    "Transitioning ticket '{0}' to '{1}' status..."
                    .format(jira_ticket, transition_to)
                    )
                jira.set_issue_status_by_transition_id(
                    jira_ticket, transition_id
                    )
                statuses_json[project_key][ticket_type] = {
                    "closed_status": transition_to,
                    "to_status": transition_to,
                    "transition_id": transition_id
                    }
            if get_value("closed_status") is None:
                print(
                    "Ticket '{0}' is not in the correct status, please check."
                    .format(jira_ticket)
                    )
        elif ticket_status == get_value("closed_status"):
            print("Ticket '{0}' is already CLOSED/DONE!".format(jira_ticket))
        elif get_value("transition_id") is None:
            transitions = get_transitions(jira, jira_ticket, ticket_status)
            transition_to = transitions[0]
            transition_id = transitions[1]
            if transition_id is not None:
                print(
                    "Transitioning ticket '{0}' to '{1}' status..."
                    .format(jira_ticket, transition_to)
                    )
                jira.set_issue_status_by_transition_id(
                    jira_ticket, transition_id
                    )
                statuses_json[project_key][ticket_type] = {
                    "closed_status": transition_to,
                    "to_status": transition_to,
                    "transition_id": transition_id
                    }
            else:
                print(
                    "Ticket '{0}' cannot be closed from status '{1}'."
                    .format(jira_ticket, ticket_status)
                    )
        elif ticket_status != get_value("closed_status"):
            transitions_result = jira.get_issue_transitions(jira_ticket)
            if len(transitions_result) != 0:
                closed = False
                for transition in transitions_result:
                    if transition["id"] == get_value("transition_id"):
                        print(
                            "Transitioning ticket '{0}' to '{1}' status..."
                            .format(jira_ticket, transition["to"])
                            )
                        jira.set_issue_status_by_transition_id(
                            jira_ticket, transition["id"]
                            )
                        closed = True
                        break
                if not closed:
                    print(
                        "Ticket '{0}' cannot be closed from status '{1}'."
                        .format(jira_ticket, ticket_status)
                        )
            else:
                print(
                    "No transition available for ticket '{0}'. Please check!"
                    .format(jira_ticket)
                    )
        else:
            print(
                "Ticket '{0}' of type '{1}' and status '{2}'\n\
                does not need to be processed"
                .format(jira_ticket, ticket_type, ticket_status)
                )

    # TODO - rewrite the json file only when there are changes
    with open(jira_statuses_file, "w+") as f:
        f.write(json.dumps(statuses_json, indent=4))
        f.write("\n")


if __name__ == "__main__":
    main()
