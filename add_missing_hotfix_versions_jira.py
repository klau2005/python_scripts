#!/usr/bin/env python3
# Compare 2 Bitbucket branches, get the diff and extract the list of merges.
# For each merge, check if it has a hotfix tag and then cross-check this with the related
# Jira ticket. If the tag is not added to the Fix Version/s, add it now
# Date: July 2019
# Author: Claudiu Tomescu
# e-mail: klau2005@tutanota.com

### Imports ###

import argparse, json, logging, re, requests, sys
from datetime import datetime as dt
from atlassian import Bitbucket, Jira

# logging config - NEEDS work!
logger = logging.getLogger("bitbucket")
logger.setLevel(level=logging.INFO)
fh = logging.StreamHandler()
logger.addHandler(fh)

### Arguments ###

parser = argparse.ArgumentParser(description = "Check if there are hotfix tags\
    in Bitbucket that are not addeed as Fix Version to the related Jira ticket")
parser.add_argument("-w", "--week", help = "Specify week number to check", type = int, required=True)
parser.add_argument("-y", "--year", help = "Specify year to check (4 digits), defaults to current one", type = int)
parser.add_argument("-t", "--test", help = "Use --test=True if you need to find out the actions about to be applied",\
    type = bool, default = False)
args = parser.parse_args()

### Variables ###

# get current year number 
iso_date = dt.isocalendar(dt.now())
curr_year = str(iso_date[0])
curr_year_short = curr_year[2:]

week_number = "{:02d}".format(args.week) # make sure it is always 2 digits (with leading zero where necessary)
year = args.year
if (year and len(year) != 4):
    logger.error("Please specify year as a 4 digits number to prevent ambiguity")
    sys.exit(1)
elif year:
    year = str(year)[2:]
else:
    year = curr_year_short
test_mode = args.test
jira_url = "https://jira.example.com"
bb_url = "https://bitbucket.example.com"
bb_project = "<project>"
bb_repo = "<repo>"
## TODO - create dedicated API user for BB/Confluence/Jira
user = "<username>"
passwd = "<password>"

# dirty check if user changed the credentials
if (user == "<username>" or passwd == "<password>"):
    logger.info("Oops, did you forget to change the username/password?\nExiting now...")
    sys.exit(1)

### Functions ###
def get_project_data(project_name, jira_conn):
    """
    gets project details for a given project; accepts as parameter the project key
    """
    result = jira_conn.project(project_name)
    return(result)

def add_project_fix_version(jira_ticket, tag_version, jira_conn):
    """
    adds missing fixVersion to Jira project
    """
    jira_project = jira_ticket.split("-")[0]
    # check if the Jira project already has the Fix Version available
    project_details = get_project_data(jira_project, jira_conn)
    try:
        project_id = project_details["id"]
        project_name = project_details["name"]
        project_versions = project_details["versions"]
    except KeyError:
        # it can happen that a project is no longer available for whatever reason...
        return
    else:
        project_versions_list = [version["name"] for version in project_versions]
        if tag_version not in project_versions_list:
            # check if running in test mode
            if not test_mode:
                logger.info("Adding missing version \"{0}\" to project \"{1}\"".format(tag_version, project_name))
                jira.add_version(project_name, project_id, tag_version)
            else:
                logger.info("Not adding version \"{0}\" to project \"{1}\" while running in test mode"\
                    .format(tag_version, project_name))

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

bitbucket = Bitbucket(
    url = bb_url,
    username = user,
    password = passwd)

jira = jiraVw(
    url = jira_url,
    username = user,
    password = passwd)

def main():
    # start with 1 as minor hotfix version and move up from it until there are no more tags
    minor_version = 1
    while True:
        tag_version = "4.{}.{}.{:02d}".format(year, week_number, minor_version)
        # get tag details from the repo
        result = bitbucket.get_project_tags(bb_project, bb_repo, tag_version)
        # if we have a result, it means this tag exists
        if result is not None:
            # get the commit number associated with this tag
            commit_id = result["latestCommit"]
            # now get the commit details (includes related Jiar tickets - what we are searching for)
            jira_ticket_details = bitbucket.get_commit_info(bb_project, bb_repo, commit_id)
            try:
                jira_ticket_list = jira_ticket_details["properties"]["jira-key"]
            except KeyError:
                # no ticket means nothing to do in Jira
                jira_ticket_list = []
            if len(jira_ticket_list) == 0:
                logger.error("The commit associated with tag \"{0}\" has no related Jira tickets."\
                    .format(tag_version))
            else:
                # go through the ticket list                
                for jira_ticket in jira_ticket_list:
                    add_project_fix_version(jira_ticket, tag_version, jira)
                    logger.info("Checking Jira ticket \"{0}\" for Fix Version \"{1}\"".format(jira_ticket, tag_version))
                    # get fixVersions for the Jira ticket
                    ticket_details = jira.issue(jira_ticket, fields = "fixVersions")
                    try:
                        ticket_versions_list = ticket_details["fields"]["fixVersions"]
                    except KeyError:
                        # either ticket doesn't exist anymore or some other error so we just continue
                        continue
                    else:
                        # get the ticket key from the response as it can be different if the ticket was moved...
                        ticket_key = ticket_details["key"]
                        # check and add missing tag version to the Jira project (necessary to check again if the ticket was moved)
                        add_project_fix_version(ticket_key, tag_version, jira)
                        ticket_versions_list = [version["name"] for version in ticket_versions_list]
                        # first check if the ticket already has 2 or more fixVersions (this shouldn't happen)
                        # and doesn't have the version we are currently checking
                        if (len(ticket_versions_list) > 1 and tag_version not in ticket_versions_list):
                            logger.error("Ticket {0}/browse/{1} has at least 2 fixVersions, please check it!".format(jira_url ,ticket_key))
                        # now check if the ticket has a fixVersion set and it is a hotfix one (but not the one we are about to add)
                        elif (len(ticket_versions_list) == 1 and tag_version not in ticket_versions_list\
                             and re.search("\d+?\.\d+?\.\d+?\.\d+$", ticket_versions_list[0])):
                            logger.error("Ticket {0}/browse/{1} has a hotfix version, please check it!".format(jira_url ,ticket_key))
                        # if the hotfix Fix Version is not set, we add it now
                        elif (len(ticket_versions_list) <= 1 and tag_version not in ticket_versions_list):
                            data = {"fixVersions": [{"name": tag_version}]}
                            for version in ticket_versions_list:
                                data["fixVersions"].append({"name": version})
                            # check if running in test mode
                            if not test_mode:
                                logger.info("Adding hotfix version \"{0}\" to ticket \"{1}\"".format(tag_version, ticket_key))
                                jira.issue_update(ticket_key, data)
                            else:
                                logger.info("Not adding Fix Version \"{0}\" to ticket \"{1}\" while running in test mode"\
                                    .format(tag_version, ticket_key))
            minor_version += 1
        else:
                break

 # run main function   
if __name__ == "__main__":
    main()
