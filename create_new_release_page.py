#!/usr/bin/env python3
# Create a new Confluence page for the current week's release
# Date: July 2019
# Author: Claudiu Tomescu
# e-mail: klau2005@tutanota.com

### Imports ###

import argparse, logging, sys
from datetime import datetime as dt
from atlassian import Bitbucket, Confluence

# logging config - NEEDS work!
logger = logging.getLogger("confluence")
logger.setLevel(level=logging.INFO)
fh = logging.StreamHandler()
logger.addHandler(fh)

### Variables ###

# get current week number and year
iso_date = dt.isocalendar(dt.now())
curr_year = str(iso_date[0])
curr_year_short = curr_year[2:]
curr_week_number = iso_date[1]

# adding here the args section as we need the week number from above...
parser = argparse.ArgumentParser(description="Create new Confluence page\
    for current week's release")
parser.add_argument("-w", "--week", help="Specify week number for the page,\
    defaults to current one", type=int, default=curr_week_number)
parser.add_argument("-c", "--create_branches", help="Set this to True if you wish to have the release branches \
    created automatically for the repos", type=bool, default=False)
parser.add_argument("-t", "--test", help="Use --test=True if you need to find out the actions about to be applied",\
    type=bool, default=False)
args = parser.parse_args()

# store the provided week number in a variable (or the current one if not provided)
page_week_number = "{:02d}".format(args.week) # make sure it is always 2 digits (with leading zero where necessary)
create_branches = args.create_branches
test_mode = args.test

# get day and month of Monday and Thursday of release week
monday_date_format = "{0} W{1} w{2}".format(curr_year, int(page_week_number) -1, 1)
monday_date_format = dt.strptime(monday_date_format, "%Y W%W w%w")
monday_day_number = monday_date_format.day
monday_month_number = monday_date_format.month
monday_month_name = monday_date_format.strftime("%b").upper()
thursday_date_format = "{0} W{1} w{2}".format(curr_year, int(page_week_number) -1, 4)
thursday_date_format = dt.strptime(thursday_date_format, "%Y W%W w%w")
thursday_day_number = thursday_date_format.day
thursday_month_number = thursday_date_format.month
thursday_month_name = thursday_date_format.strftime("%b").upper()

operator_major_version = 4

operator_version = "{0}.{1}.{2}".format(operator_major_version, curr_year_short, page_week_number)

core_label = "core-{0}-{1}-{2}".format(operator_major_version, curr_year_short, page_week_number)
week_label = "week-{0}-{1}".format(curr_year, page_week_number)

created_color = "Green"
created_date = "{0} {1}".format(monday_month_name, monday_day_number)

deployed_to_stg_avance_color = "Green"
deployed_to_stg_avance_date = created_date

deployed_to_prod_color = "Yellow"
deployed_to_prod_date = "{0} {1}".format(thursday_month_name, thursday_day_number)

confluence_url = "https://confluence.example.com"
confluence_username = "<username>" # use your own here
confluence_password = "<password>" # use your own here
confluence_space = "OO" # Operations - Operator
confluence_page_title = "Operator {0}".format(operator_version)
confluence_parent_page_title = "Operator Core {0}".format(curr_year)
confluence_page_labels = ["pipeline", "pipeline-details", "staging", core_label, week_label]

bb_url = "https://bitbucket.example.com"
bb_username = "<username>" # use your own here
bb_password = "<password>" # use your own here
bb_project = "OP" # Operator
bb_operator_repo = "operator"
bb_scripts_repo = "scripts"
bb_branch = "release/{0}".format(operator_version)
bb_source_branch = "develop"

# dirty check if user changed the credentials
if ((confluence_username == "<username>" or bb_username == "<username>") or (confluence_password == "<password>" or bb_password == "<password>")):
    logger.error("Oops, did you forget to change the username/password?\nExiting now...")
    sys.exit(1)

# variable that stores the data to be posted to Confluence; this is the XHTML representing page data
page_data = '<p>JIRA:&nbsp;<a href="https://jira.example.com/issues/?jql=fixVersion%20in%20(%22Operator%20{operator_version}%22)">{operator_version}</a></p>\
    <p>&nbsp;</p>\
    <ac:structured-macro ac:name="details" ac:schema-version="1" ac:macro-id="18915ac1-3c31-45d7-a226-be3665c89f99">\
    <ac:parameter ac:name="id">summ</ac:parameter>\
    <ac:rich-text-body>\
    <p class="auto-cursor-target"><br /></p>\
    <table class="wrapped">\
    <colgroup>\
    <col style="width: 109.0px;" />\
    <col style="width: 408.0px;" />\
    <col style="width: 210.0px;" />\
    <col style="width: 179.0px;" />\
    </colgroup>\
    <tbody>\
    <tr>\
    <th colspan="1">Created</th>\
    <th colspan="1">Release Candidates</th>\
    <th>Deployed to Staging/Avance</th>\
    <th colspan="1">Deployed to Production</th>\
    </tr>\
    <tr>\
    <td colspan="1">\
    <div class="content-wrapper">\
    <p>\
    <ac:structured-macro ac:name="status" ac:schema-version="1" ac:macro-id="babfcc92-6dee-487b-96f3-d4f34e2f937f">\
    <ac:parameter ac:name="colour">{created_color}</ac:parameter>\
    <ac:parameter ac:name="title">{created_date}</ac:parameter>\
    <ac:parameter ac:name="" />\
    </ac:structured-macro>\
    </p>\
    </div>\
    </td>\
    <td colspan="1">\
    <div class="content-wrapper">\
    <p>\
    <ac:structured-macro ac:name="detailssummary" ac:schema-version="2" ac:macro-id="2446c6cf-a3ae-495a-acde-132966614fc1">\
    <ac:parameter ac:name="firstcolumn">Version</ac:parameter>\
    <ac:parameter ac:name="headings">Created, Summary</ac:parameter>\
    <ac:parameter ac:name="sortBy">Title</ac:parameter>\
    <ac:parameter ac:name="id">summ</ac:parameter>\
    <ac:parameter ac:name="label">{core_label}</ac:parameter>\
    <ac:parameter ac:name="cql">label = &quot;{core_label}&quot; and space = currentSpace()</ac:parameter>\
    </ac:structured-macro>\
    </p>\
    </div>\
    </td>\
    <td colspan="1">\
    <div class="content-wrapper">\
    <p><br /></p>\
    </div>\
    <ac:structured-macro ac:name="status" ac:schema-version="1" ac:macro-id="46fed590-4602-4513-a079-899c0f722d3a">\
    <ac:parameter ac:name="colour">{deployed_to_stg_avance_color}</ac:parameter>\
    <ac:parameter ac:name="title">{deployed_to_stg_avance_date}</ac:parameter>\
    <ac:parameter ac:name="" />\
    </ac:structured-macro>\
    </td>\
    <td colspan="1">\
    <div class="content-wrapper">\
    <p><br /></p>\
    <ac:structured-macro ac:name="status" ac:schema-version="1" ac:macro-id="3f37ba60-1610-4c77-bcf3-650414601c3c">\
    <ac:parameter ac:name="colour">{deployed_to_prod_color}</ac:parameter>\
    <ac:parameter ac:name="title">{deployed_to_prod_date}</ac:parameter>\
    <ac:parameter ac:name="" />\
    </ac:structured-macro>\
    </div>\
    </td>\
    </tr>\
    </tbody>\
    </table>\
    <p class="auto-cursor-target"><br /></p>\
    </ac:rich-text-body>\
    </ac:structured-macro>\
    <p class="auto-cursor-target"><br /></p>\
    <p><br /></p>\
    <ac:structured-macro ac:name="details" ac:schema-version="1" ac:macro-id="87acc734-f85f-4e80-a072-ed03c30775be">\
    <ac:parameter ac:name="id">details</ac:parameter>\
    <ac:rich-text-body>\
    <p class="auto-cursor-target"><br /></p>\
    <table class="wrapped">\
    <colgroup><col /></colgroup>\
    <tbody>\
    <tr><th>Content</th></tr>\
    <tr>\
    <td>\
    <div class="content-wrapper">\
    <p><ac:structured-macro ac:name="jira" ac:schema-version="1" ac:macro-id="e9b261d4-6aa8-4c02-87d9-457d64eea531">\
    <ac:parameter ac:name="server">JIRA</ac:parameter>\
    <ac:parameter ac:name="columns">key,summary,status,operator ticket,project,resolution,product team,fixversions,deployment notes</ac:parameter>\
    <ac:parameter ac:name="maximumIssues">1000</ac:parameter>\
    <ac:parameter ac:name="jqlQuery">fixVersion in (&quot;Operator {operator_version}&quot;)  order by key</ac:parameter>\
    <ac:parameter ac:name="serverId">89d4a9b8-fab9-3586-8565-84e171ae9ff1</ac:parameter>\
    </ac:structured-macro>\
    </p>\
    </div>\
    </td>\
    </tr>\
    </tbody>\
    </table>\
    <p class="auto-cursor-target"><br /></p>\
    </ac:rich-text-body>\
    </ac:structured-macro>\
    <p>&nbsp;</p><hr />'\
    .format(operator_version = operator_version, core_label = core_label, created_color = created_color,\
    created_date = created_date, deployed_to_stg_avance_color = deployed_to_stg_avance_color,\
    deployed_to_stg_avance_date = deployed_to_stg_avance_date, deployed_to_prod_color = deployed_to_prod_color,\
    deployed_to_prod_date = deployed_to_prod_date)

### Main section ###
def main():
    # instantiate a new Confluence object
    confluence = Confluence(
        url = confluence_url,
        username = confluence_username,
        password = confluence_password)

    # instantiate a new Bitbucket object
    bitbucket = Bitbucket(
        url = bb_url,
        username = bb_username,
        password = bb_password)

    # first get the parent page ID
    page_id_result = confluence.get_page_by_title(space = confluence_space, title = confluence_parent_page_title)
    try:
        confluence_parent_page_id = page_id_result["id"]
    except Exception:
        logger.warning("Can't get ID for parent page {0}".format(confluence_parent_page_title))
        sys.exit(1)
    # check if in test mode
    if not test_mode:
        # first create the release branches (if the proper parameter was passed to the script)
        if create_branches:
            operator_branch_result = bitbucket.create_branch(bb_project, bb_operator_repo, bb_branch, bb_source_branch)
            try:
                operator_error = operator_branch_result["errors"]
            except KeyError:
                logger.info("Branch \"{0}\" of repo \"{1}\" was successfully forked from \"{2}\"".format(bb_branch, bb_operator_repo, bb_source_branch))
            else:
                logger.warning("Failed to create branch, error:\n{0}".format(operator_error[0]["message"]))

            scripts_branch_result = bitbucket.create_branch(bb_project, bb_scripts_repo, bb_branch, bb_source_branch)
            try:
                scripts_error = scripts_branch_result["errors"]
            except KeyError:
                logger.info("Branch \"{0}\" of repo \"{1}\" was successfully forked from \"{2}\"".format(bb_branch, bb_scripts_repo, bb_source_branch))
            else:
                logger.warning("Failed to create branch, error:\n{0}".format(scripts_error[0]["message"]))
        
        # send the create_page API call
        create_page_result = confluence.create_page(space = confluence_space, title = confluence_page_title,\
            parent_id = confluence_parent_page_id, body = page_data)
        # check if it was successful
        try:
            create_page_result["status"]
        except KeyError:
            logger.error("Could not create page.\nReason: \"{0}\"".format(create_page_result["message"]))
            sys.exit(1)
        except Exception:
            logger.error("Could not create page. Unknown reason...")
            sys.exit(1)
        else:
            # get newly created page ID and set the necessary labels (it needs to be done after creating it)
            page_id = create_page_result["id"]
            for label in confluence_page_labels:
                confluence.set_page_label(page_id, label)
            logger.info("Page \"{0}/display/{1}/Operator+{2}\" created successfully!".format(confluence_url,\
                confluence_space, operator_version))
    else:
        logger.info("Creating Confluence page \"{0}\" under \"{1}\" in space \"{2}\".".format(confluence_page_title,\
            confluence_parent_page_title, confluence_space))
        logger.info("Creating Bitbucket branch \"{0}\" in \"{1}\" repository.".format(bb_branch, bb_operator_repo))
        logger.info("Creating Bitbucket branch \"{0}\" in \"{1}\" repository.".format(bb_branch, bb_scripts_repo))

# run main function
if __name__ == "__main__":
    main()
