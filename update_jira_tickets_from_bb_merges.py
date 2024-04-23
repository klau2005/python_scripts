#!/usr/bin/env python3
# Compare 2 different BitBucket branches, get all merges and get list of related Jira tickets
# it will first check if the tickets' projects already have that version, if not, it will be added
# next it will check if the tickets already have a Fix Version/s set (shouldn't happen...)
# and add the proper one if none available
# Date: July 2019
# Author: Claudiu Tomescu
# e-mail: klau2005@tutanota.com

### Imports ###

import argparse, json, logging, re, requests, sys
from atlassian import Bitbucket, Jira

# logging config - NEEDS work!
logger = logging.getLogger("bitbucket")
logger.setLevel(level=logging.INFO)
fh = logging.StreamHandler()
logger.addHandler(fh)

### Arguments ###

parser = argparse.ArgumentParser(description = "Add the Fix Version to Jira tickets\
        related to the specified week BitBucket merges")
parser.add_argument("--from_repo", help = "Repository holding the changes", type = str, required=True)
parser.add_argument("--to_repo", help = "Repository to compare against", type = str, required=True)
parser.add_argument("--test", help = "Use --test=True if you need to find out the actions about to be applied",\
    type = bool, default = False)
args = parser.parse_args()

### Variables ###

from_branch = args.from_repo
to_branch = args.to_repo
test_mode = args.test
if re.match("release/", from_branch):
    version_number = from_branch.split("/")[1]
    operator_fix_version = "Operator {0}".format(version_number)
else:
    logger.error("Can't proceed without a relase branch as source branch to compare, exiting...")
    sys.exit(1)
jira_url = "https://jira.example.com"
bb_url = "https://bitbucket.example.com"
## TODO - create dedicated API user for BB/Confluence/Jira
user = "<username>" # use your own here
passwd = "<password>" # use your own here

# dirty check if user changed the credentials
if (user == "<username>" or passwd == "<password>"):
    logger.info("Oops, did you forget to change the username/password?\nExiting now...")
    sys.exit(1)

### Functions ###
def get_project_data(project_name, jira_conn):
    """gets project details for a given project; accepts as parameter the project key"""
    result = jira_conn.project(project_name)
    return(result)

### Classes ###
class jiraVw(Jira):
    def add_version(self, project_name, project_id, version):
        """
        Extend base Jira class with new method to add missing version to project
        :param project_name:
        :param project_id:
        :param version:
        :return:
        """
        payload = {'name': version, 'archived': False, 'released': False, 'project': project_name, 'projectId': project_id}
        return self.post("rest/api/2/version", data = payload)

### Main ###
def main():
    bitbucket = Bitbucket(
        url = bb_url,
        username = user,
        password = passwd)

    jira = jiraVw(
        url = jira_url,
        username = user,
        password = passwd)

    logger.info("Get diff between branch \"{0}\" and \"{1}\"".format(from_branch, to_branch))
    changelog = bitbucket.get_changelog(
        project = "OP",
        repository = "operator",
        ref_from = from_branch,
        ref_to = to_branch)

    jira_tickets = set()
    jira_projects = set()

    # iterate over the list of commits and check for merges
    logger.info("Processing list of changes...")
    nb_merges = 0
    # quick sanity check to see if we got the repos correct
    if not changelog:
        logger.error("BB diff returned None, there are either no changes or repository names are wrong, nothing to do")
        sys.exit(1)
    # iterate over the items in the changelog
    for item in changelog:
        message = item['message']
        try:
            jira_keys = item['properties']['jira-key']
        except KeyError:
            jira_keys = []
        if (message.startswith("Merge")):
            nb_merges += 1
            for item in jira_keys:
                jira_tickets.add(item)
    logger.info("Found {0} merges".format(nb_merges))

    # save the unique list of sorted JIRA tickets
    jira_tickets = list(jira_tickets)
    jira_tickets.sort()
    logger.info("Jira tickets that show up in the diff:")
    for ticket in jira_tickets:
        logger.info("{0}/browse/{1}".format(jira_url, ticket))

    # save the unique list of JIRA projects
    for ticket in jira_tickets:
        project = ticket.split("-")[0]
        jira_projects.add(project)

    # get projectId for all projects in our list and save the project name and project id in a dictionary
    # also check if the version we want to add is already available for this project
    jira_projects_dict = {}
    logger.info("Jira projects list:")
    for project in jira_projects:
        project_details = get_project_data(project, jira)
        try:
            project_id = project_details["id"]
            project_name = project_details["name"]
            project_versions = project_details["versions"]
        except KeyError:
            # it can happen that a project is no longer available for whatever reason...
            continue
        else:
            logger.info("{0} - {1}".format(project, project_name))
            jira_projects_dict[project] = {"ID": project_id}
            version_available = False
            for version in project_versions:
                version_name = version["name"]
                if version_name == operator_fix_version:
                    version_available = True
            jira_projects_dict[project]["has_version"] = version_available

    # add the missing versions
    for project in jira_projects_dict.keys():
        project_name = project
        project_id = jira_projects_dict[project]["ID"]
        version_available = jira_projects_dict[project]["has_version"]
        if not version_available:
            # check if running in test mode
            if not test_mode:
                logger.info("Adding missing version \"{0}\" for project \"{1}\"".format(operator_fix_version, project_name))
                jira.add_version(project_name, project_id, operator_fix_version)
            else:
                logger.info("Skip adding new version \"{0}\" for project \"{1}\" while running in test mode..."\
                    .format(operator_fix_version, project_name))

    # go through the list of tickets and check which one doesn't have any Fix Version set
    logger.info("Start adding missing Fix Versions to Jira tickets")
    for ticket in jira_tickets:
        ticket_details = jira.issue(ticket, fields = "fixVersions")
        try:
            versions_list = ticket_details["fields"]["fixVersions"]
        except KeyError:
            # either ticket doesn't exist anymore or some other error so we just continue
            continue
        else:
            # if there is no Fix Version set, we add the Operator one now
            if len(versions_list) == 0:
                # check if running in test mode
                if not test_mode:
                    logger.info("Ticket \"{0}\" has no Fix Version set, adding \"{1}\"".format(ticket, operator_fix_version))
                    data = {"fixVersions": [{"name": operator_fix_version}]}
                    jira.issue_update(ticket, data)
                else:
                    logger.info("Not updating Fix Version field for ticket \"{0}\" while in test mode:".format(ticket))
            # if there is at least a version added
            elif len(versions_list) > 0:
                # define a bool variable for storing if one of the versions in the ticket is the one we want to add
                has_desired_op_version = False
                # second bool variable for storing if the ticket already has an Operator version added
                has_different_op_version = False
                # now go through every version in the list
                for version in versions_list:
                    version = version["name"]
                    # ticket already has the desired Operator version
                    if version == operator_fix_version:
                        has_desired_op_version = True
                        continue
                    # ticket has another Operator version
                    elif re.search("Operator", version):
                        has_different_op_version = True
                        continue
                if has_desired_op_version and has_different_op_version:
                    # ticket has at least 2 Operator versions, including the desired one
                    logger.error("Ticket {0}/browse/{1} has multiple Operator versions set, please check it!".format(jira_url, ticket))
                elif has_different_op_version:
                    logger.error("Ticket {0}/browse/{1} has another Operator version set, please check it!".format(jira_url, ticket))
                elif not has_desired_op_version and not has_different_op_version:
                    # ticket does not have any Operator version set so we add it now
                    # check if running in test mode
                    if not test_mode:
                        logger.info("Adding Operator Version \"{0}\" to ticket \"{1}\"".format(operator_fix_version, ticket))
                        data = {"fixVersions": [{"name": operator_fix_version}]}
                        for version in versions_list:
                            data["fixVersions"].append({"name": version["name"]})
                        #print(data)
                        jira.issue_update(ticket, data)
                    else:
                        logger.info("Not updating Fix Version field for ticket \"{0}\" while in test mode".format(ticket))

# run main function
if __name__ == "__main__":
    main()
