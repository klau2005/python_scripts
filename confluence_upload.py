#!/usr/bin/env python3
# Upload K8S resources data to Confluence
# Date: May 2017
# Author: Claudiu Tomescu
# e-mail: klau2005@gmail.com

import sys, requests
from requests.auth import HTTPBasicAuth
from datetime import datetime as dt
import mysql.connector
from mysql.connector import errorcode

### Variables section ###
hist = 7
api_user = "api_user"
api_passwd = "api_pass"
headers = {"Content-Type": "application/json"}
base_url = "<URL>/rest/api/content"
space_name = "space_name"
page_name = "page_name"
page_url = "{}?title={}&spaceKey={}&expand=version".format(base_url, page_name, space_name)
platform_dict = {'hsa-gsma': 'HSA GSMA Cluster', 'sca-prd': 'SCA PROD Cluster', 'sca-stg': 'SCA STAGING Cluster'}
# static HTML table header
table_header = '<table><tr><th>SERVER</th><th>K8S CPU NUMBER</th><th>K8S CPU LIMITS</th>\
<th>K8S CPU LIMITS &#37;</th><th>K8S CPU REQUESTS</th><th>K8S CPU REQUESTS &#37;</th>\
<th>K8S MEMORY CAPACITY</th><th>K8S MEMORY LIMITS</th><th>K8S MEMORY LIMITS &#37;</th>\
<th>K8S MEMORY REQUESTS</th><th>K8S MEMORY REQUESTS &#37;</th><th>TOTAL RAM</th>\
<th>AVAILABLE RAM</th></tr>'
# and the footer
table_footer = '</table>'
# define DB parameters
config = {
  'user': 'db_user',
  'password': 'db_pass',
  'host': 'db_host',
  'database': 'k8s',
  'raise_on_warnings': True,
}
# date variables
# get current year/month/day
curr_year = dt.timetuple(dt.utcnow()).tm_year
curr_month = dt.timetuple(dt.utcnow()).tm_mon
curr_day = dt.timetuple(dt.utcnow()).tm_mday
# transform into date string in format <year>-<month>-<day>
curr_date = "{}-{}-{}".format(curr_year, curr_month, curr_day)
# transform into date object (we get clean date, with 00:00 for time, end of report date)
end_date = dt.strptime(curr_date, '%Y-%m-%d')
# get report end unixtime from that date object
end_unixtime = int(dt.strftime(end_date, '%s'))
# and finally, get unixtime for report start date, 7 days back
time_diff = 60 * 60 * 24 * hist # get seconds for 7 days back
start_unixtime = end_unixtime - time_diff
# get datetime object from start_unixtime (we'll need it to extract start of report week)
start_date = dt.fromtimestamp(start_unixtime)
# get report year
report_year = start_date.isocalendar()[0]
# get report week number
report_week = start_date.isocalendar()[1]
# get report number in <year-week> format (for last week, report week)
report_number = "{}-{}".format(report_year, report_week)

### Functions section ###
# function to create list of servers for certain platform
def gen_srv_list(platform):
    srv_list = []
    query = "SELECT DISTINCT(server_name) FROM k8s_report WHERE platform = '{}'"\
    .format(platform)
    cursor.execute(query)
    for line in cursor:
        srv_list.append(line[0])
    return srv_list

# function to get data from DB for certain server/platform
def k8s_data(platform, srv):
    # define SELECT query
    query = "SELECT server_name, k8s_cpu_no, k8s_cpu_limits,\
    k8s_cpu_limits_perc, k8s_cpu_requests, k8s_cpu_requests_perc,\
    k8s_mem_capacity, k8s_mem_limits, k8s_mem_limits_perc,\
    k8s_mem_requests, k8s_mem_requests_perc,\
    total_ram, available_ram FROM k8s_report WHERE report_week = '{0}'\
    AND platform = '{1}' AND server_name = '{2}' LIMIT 1".format(report_number, platform, srv)
    # run query in DB and store result in tuple
    cursor.execute(query)
    for line in cursor:
        result = line
    return result

# function to create update data for Confluence
def gen_data(list):
    table_data = ""
    for srv in list:
        server = k8s_data(platform, srv)[0]
        cpu_no = k8s_data(platform, srv)[1]
        cpu_limits = k8s_data(platform, srv)[2]
        cpu_limits_perc = k8s_data(platform, srv)[3]
        cpu_requests = k8s_data(platform, srv)[4]
        cpu_requests_perc = k8s_data(platform, srv)[5]
        mem_capacity = k8s_data(platform, srv)[6]
        mem_limits = k8s_data(platform, srv)[7]
        mem_limits_perc = k8s_data(platform, srv)[8]
        mem_requests = k8s_data(platform, srv)[9]
        mem_requests_perc = k8s_data(platform, srv)[10]
        total_ram = k8s_data(platform, srv)[11]
        available_ram = k8s_data(platform, srv)[12]
        # format data to be used in the request
        row_data = '<tr><td>{0}</td><td>{1}</td><td>{2}</td><td>{3}</td><td>{4}</td>\
        <td>{5}</td><td>{6}</td><td>{7}</td><td>{8}</td><td>{9}</td><td>{10}</td>\
        <td>{11}</td><td>{12}</td></tr>'.format(server, cpu_no, cpu_limits,\
        cpu_limits_perc, cpu_requests, cpu_requests_perc, mem_capacity, mem_limits,\
        mem_limits_perc, mem_requests, mem_requests_perc, total_ram, available_ram)
        table_data += row_data
    return table_data

### DB section ###
# open connection to DB
try:
    cnx = mysql.connector.connect(**config)
    cursor = cnx.cursor()
except mysql.connector.Error as err:
    if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
        print("Something is wrong with your user name or password")
        sys.exit(2)
    elif err.errno == errorcode.ER_BAD_DB_ERROR:
        print("Database does not exist")
        sys.exit(2)
    else:
        print(err)
        sys.exit(2)

# define variable that will store data to be uploaded to Confluence
confluence_data = ""

# function to populate confluence variable with needed data
for platform in platform_dict.keys():
    confluence_data += '<h2>{}</h2>'.format(platform_dict[platform])
    confluence_data += table_header
    srv_list = gen_srv_list(platform)
    confluence_data += gen_data(srv_list)
    confluence_data += table_footer

### Confluence API section ###
# connect to API and get page ID and page version
try:
    response = requests.get(page_url, auth = HTTPBasicAuth(api_user, api_passwd))
except Exception as e:
    print(e)
    print("Cannot connect to Confluence, please check site/link")
    sys.exit(2)
else:
    if response.status_code == 200:
        page_id = response.json()['results'][0]['id']
        page_ver = response.json()['results'][0]['version']['number']
        update_data = '{{"id": "{ID}", "status": "current", "version": {{"number": {version}}},\
        "space": {{"key": "{space}"}}, "type": "page", "title": "{page}", "body": {{"storage": {{\
        "value": "{data}", "representation": "storage"}}}}}}'.format(ID = page_id, \
        version = page_ver + 1, space = space_name, page = page_name, data = confluence_data)
    else:
        print("Something went wrong, exiting...")
        sys.exit(2)

# define Confluence page URL    
update_url = "{}/{}".format(base_url, page_id)

try:
    response = requests.put(update_url, update_data, headers = headers, auth = HTTPBasicAuth(api_user, api_passwd))
except Exception as e:
    print(e)
    print("Cannot connect to Confluence, please check site/link")
    sys.exit(2)
else:
    if response.status_code == 200:
        print("Data successfully uploaded!")
        sys.exit(0)
    else:
        print(response.json())
        print("Something went wrong, exiting...")
        sys.exit(2)
