#!/usr/bin/env python3
# K8S cluster resources allocation and usage
# this script gets data from both K8S master and from Zabbix
# Date: April 2017
# Author: Claudiu Tomescu
# e-mail: klau2005@gmail.com

import re, sys, requests
from pexpect import pxssh
from datetime import datetime as dt
import mysql.connector
from mysql.connector import errorcode

def usage():
    print("Usage {} <sca-prd|sca-stg>".format(sys.argv[0]))
    sys.exit(1)

if len(sys.argv) != 2:
    usage()

###FIRST STEP - K8S DATA###
# variables for k8s connection
platform = sys.argv[1]
if platform == "sca-stg":
    k8s_hostname = '<IP>'
    report_file = "/home/claudtom/scripts/k8s_weekly_report_sca_stg"
elif platform == "sca-prd":
    k8s_hostname = '<IP>'
    report_file = "/home/claudtom/scripts/k8s_weekly_report_sca_prd"
else:
    usage()

# define history variable (how many days of history to extract from Zabbix)
hist = 7
# k8s master node username and password
k8s_username = '<ssh_username>'

# define various functions
# standardize all hostnames into caps and no smctr.net format
# e.g from ro1s1adm00001v.smctr.net into RO1S1ADM00001V
def normalize_name(hostname):
    hostname = hostname.rstrip(".smctr.net")
    hostname = hostname.upper()
    return hostname

# convert full CPU resource value from k8s into milicpu format (eg. from 1 to 1000)
def conv_cpu_val(val):
    if not "m" in val:
        result = int(val) * 1000
    else:
        result = int(val.strip("m"))
    return result

# convert memory resource value from k8s from KB/GB into MB (eg. from 4046588Ki to 3951 or from 2Gi to 2048Mi)
def conv_mem_val(val):
    if "K" in val:
        result = int(val.strip("Ki")) // 1024
    elif "G" in val:
        result = int(val.strip("Gi")) * 1024
    else:
        result = int(val.strip("Mi"))
    return result

# create function to extract metrics from k8s raw data
def get_k8s_value(data, metric):
    i = 0
    while i < len(data)-3: # we don't go further as this is the last line we care about
        # search for the line that contains "Capacity:" to get CPU and memory allocated
        if re.match("^ *Capacity:", data[i]):
            # if we need CPUs number, search for the second line after the match
            if metric == "cpus_number":
                metric_line = i+2
                value = data[metric_line].split("\\t")[-1]
            # if we need memory size, search for the third line after the match
            elif metric == "memory_capacity":
                metric_line = i+3
                value = conv_mem_val(data[metric_line].split("\\t")[-1])
        # search for the line that starts with "CPU Requests" to get resource usage
        elif re.match("^ *CPU Requests", data[i]):
            metric_line = i+2
            if metric == "cpu_requests":
                value = conv_cpu_val(data[metric_line].split()[0])
            elif metric == "cpu_requests_perc":
                value = data[metric_line].split()[1].split("\\t")[0].strip("()").strip("%")
            elif metric == "cpu_limits":
                value = conv_cpu_val(data[metric_line].split()[1].split("\\t")[-1])
            elif metric == "cpu_limits_perc":
                value = data[metric_line].split()[2].split("\\t")[0].strip("()").strip("%")
            elif metric == "mem_requests":
                value = conv_mem_val(data[metric_line].split()[2].split("\\t")[-1])
            elif metric == "mem_requests_perc":
                value = data[metric_line].split()[3].split("\\t")[0].strip("()").strip("%")
            elif metric == "mem_limits":
                value = conv_mem_val(data[metric_line].split()[3].split("\\t")[-1])
            elif metric == "mem_limits_perc":
                value = data[metric_line].split()[4].strip("()").strip("%")
        i+=1
    return value

# convert RAM value from B to MB
def bytes_to_mbytes(val):
    result = int(val) // 1024 // 1024
    return result

# function to calculate average value from zabbix history data
# we do this as trends.get API call fails so we use history.get call
# please share with me if you make it work for non-float items
def get_average(data):
    # create empty list to hold all history values
    value_list = []
    # populate list with values (ints)
    for item in data:
        value_list.append(int(item['value']))
    # calculate average and return value
    average_val = sum(value_list) // len(value_list) if len(value_list) != 0 else 0
    return average_val

# define empty dictionary to store nodes and raw metrics from kubectl describe command
nodes_dict = {}
# create dictionary for storing final data to generate report from
report_dict = {}

print("Running kubectl commands on {} cluster to get nodes/stats...".format(sys.argv[1]))
# connect through SSH and run kubectl command to get nodes/stats from cluster
# this assumes we have a passwordless SSH key in standard location, like .ssh/id_rsa
# if the key is protected by a password, we must suply 3rd parameter to login function
# ex. s.login(k8s_hostname, k8s_username, k8s_passwd), where k8s_passwd is the key password
try:
    s = pxssh.pxssh()
    s.login(k8s_hostname, k8s_username)
    s.sendline("kubectl get no | awk '!/NAME/{print $1}'") # get nodes
    s.prompt() # match the prompt
    nodes = str(s.before) # print everything before the prompt.
    # save the nodes in the report dictionary as keys
    for srv in nodes.split("\\r\\n")[1:-1]:
        report_dict[srv] = {}
    # iterate over nodes list and get metrics for each using kubectl describe command
    for srv in report_dict.keys():
        comm = "kubectl describe no {}".format(srv)
        s.sendline(comm)
        s.prompt()
        # fill nodes dictionary with {"host": ["raw_values"]} data
        nodes_dict[srv] = str(s.before).split("\\r\\n")
    s.logout()
except pxssh.ExceptionPxssh as e:
    print("pxssh failed on login.")
    print(e)
    sys.exit(2)

print("Success")

# populate report dictionary with needed metrics
for srv in nodes_dict.keys():
    report_dict[srv]["CPUs number"] = get_k8s_value(nodes_dict[srv], "cpus_number")
    report_dict[srv]["Memory capacity"] = get_k8s_value(nodes_dict[srv], "memory_capacity")
    report_dict[srv]["CPU requests"] = get_k8s_value(nodes_dict[srv], "cpu_requests")
    report_dict[srv]["CPU requests percent"] = get_k8s_value(nodes_dict[srv], "cpu_requests_perc")
    report_dict[srv]["CPU limits"] = get_k8s_value(nodes_dict[srv], "cpu_limits")
    report_dict[srv]["CPU limits percent"] = get_k8s_value(nodes_dict[srv], "cpu_limits_perc")
    report_dict[srv]["Memory requests"] = get_k8s_value(nodes_dict[srv], "mem_requests")
    report_dict[srv]["Memory requests percent"] = get_k8s_value(nodes_dict[srv], "mem_requests_perc")
    report_dict[srv]["Memory limits"] = get_k8s_value(nodes_dict[srv], "mem_limits")
    report_dict[srv]["Memory limits percent"] = get_k8s_value(nodes_dict[srv], "mem_limits_perc")

# at this step, we are done with k8s processing so we delete unused dictionary
del nodes_dict

###SECOND STEP - ZABBIX DATA###
# variables for Zabbix API connection
zabbix_url = '<zabbix_url>/api_jsonrpc.php'
headers = {"Content-Type": "application/json"}
zabbix_username = 'zabbix_api_user'
zabbix_password = 'password'
zabbix_auth_req = '{{"jsonrpc": "2.0", "method": "user.login", "params": {{"user": "{}", \
"password": "{}"}}, "id": 1, "auth": null}}'.format(zabbix_username, zabbix_password)
zabbix_auth_req = zabbix_auth_req.encode()

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

print("Connect to Zabbix API to get metrics...")
# start getting data from Zabbix API
# first get connection token
response = requests.post(zabbix_url, zabbix_auth_req, headers = headers)
token = response.json()['result']

# create dictionary to store different values from Zabbix (hostid, itemid)
zabbix_dict = {}

for srv in report_dict.keys():
    zabbix_dict[srv] = {}

# get and store item ids for total memory and available memory
for srv in report_dict.keys():
    tot_mem_id_req = '{{"jsonrpc": "2.0", "method": "item.get", "params": {{"output": "itemid", "host": "{}", \
    "search": {{"key_": "vm.memory.size[total]"}},  "sortfield": "name"}}, "auth": "{}", "id": 1}}'.format(srv, token)
    result = requests.post(zabbix_url, tot_mem_id_req, headers = headers).json()['result'][0]['itemid']
    zabbix_dict[srv]["tot_mem_id"] = result

for srv in report_dict.keys():
    avail_mem_id_req = '{{"jsonrpc": "2.0", "method": "item.get", "params": {{"output": "itemid", "host": "{}", \
    "search": {{"key_": "vm.memory.size[available]"}},  "sortfield": "name"}}, "auth": "{}", "id": 1}}'.format(srv, token)
    result = requests.post(zabbix_url, avail_mem_id_req, headers = headers).json()['result'][0]['itemid']
    zabbix_dict[srv]["avail_mem_id"] = result

# add Zabbix history values for total and available memory to report dictionary
for srv in zabbix_dict.keys():
    print("Getting data for {}...".format(srv))
    for item in zabbix_dict[srv].keys():
        item_id = zabbix_dict[srv][item]
        hist_req = '{{"jsonrpc": "2.0", "method": "history.get", "params": {{"output": "extend", "history": 3, "itemids": "{}", \
        "time_from": "{}", "time_till": "{}"}}, "auth": "{}", "id": 1}}'.format(item_id, start_unixtime, end_unixtime, token)
        avg_value = requests.post(zabbix_url, hist_req, headers = headers).json()['result']
        avg_value = get_average(avg_value)
        # define new dictionary keys named <item_name_avg> (for eg. tot_mem_avg)
        item_name = item.rstrip("id") + "avg"
        report_dict[srv][item_name] = bytes_to_mbytes(avg_value)
    print("done")

print("Success")

print("Adding data to DB...")

###THIRD STEP - DB###
# define DB parameters
config = {
  'user': 'db_user',
  'password': 'db_pass',
  'host': 'db_host',
  'database': 'k8s',
  'raise_on_warnings': True,
}

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

# iterate over dictionary
for srv in sorted(report_dict):
    # define insert query for each server
    ins_query = "INSERT INTO k8s_report (\
    report_week,\
    platform,\
    server_name,\
    k8s_cpu_no,\
    k8s_cpu_limits,\
    k8s_cpu_limits_perc,\
    k8s_cpu_requests,\
    k8s_cpu_requests_perc,\
    k8s_mem_capacity,\
    k8s_mem_limits,\
    k8s_mem_limits_perc,\
    k8s_mem_requests,\
    k8s_mem_requests_perc,\
    total_ram,\
    available_ram) VALUES (\
    '{0}', '{1}', '{2}', '{3}', '{4}', '{5}', '{6}', '{7}', '{8}', '{9}', '{10}', '{11}', '{12}', '{13}',\
    '{14}')".format(report_number, platform, normalize_name(srv),\
    report_dict[srv]['CPUs number'], report_dict[srv]['CPU limits'],\
    report_dict[srv]['CPU limits percent'], report_dict[srv]['CPU requests'],\
    report_dict[srv]['CPU requests percent'], report_dict[srv]['Memory capacity'],\
    report_dict[srv]['Memory limits'], report_dict[srv]['Memory limits percent'],\
    report_dict[srv]['Memory requests'], report_dict[srv]['Memory requests percent'],\
    report_dict[srv]['tot_mem_avg'], report_dict[srv]['avail_mem_avg'])
    try:
        # insert into DB
        cursor.execute(ins_query)
        cnx.commit()
    except mysql.connector.Error as err:
        print(err)
        print("DB insert failed.")
        sys.exit(2)

cursor.close()
cnx.close()

###FOURTH STEP - FILE REPORT###
# append week number to end of report filename
report_file = "{}_{}".format(report_file, report_number)

print("Creating report file {}...".format(report_file))

# write report file in csv format to disk
try:
    with open(report_file, "a") as report:
    # write header line first
        report.write("Server,K8S CPUs number,K8S CPU limits,K8S CPU limits percent,K8S CPU requests,\
        K8S CPU requests percent,K8S Memory capacity(MB),K8S Memory limits(MB),K8S Memory limits percent,K8S Memory requests(MB),\
        K8S Memory requests percent,Server total RAM average(MB), Server available RAM average(MB)\n")
        # iterate over dictionary and append the values to the file
        for srv in sorted(report_dict):
            # enclose in a try/except statement as I found ocasionally some server returns no data
            try:
                report.write("{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},{10},{11},{12}\n".format(normalize_name(srv), report_dict[srv]['CPUs number'], \
                report_dict[srv]['CPU limits'], report_dict[srv]['CPU limits percent'], report_dict[srv]['CPU requests'], \
                report_dict[srv]['CPU requests percent'], report_dict[srv]['Memory capacity'], report_dict[srv]['Memory limits'], \
                report_dict[srv]['Memory limits percent'], report_dict[srv]['Memory requests'], \
                report_dict[srv]['Memory requests percent'], report_dict[srv]['tot_mem_avg'], report_dict[srv]['avail_mem_avg']))
            # in case no data returned, write 0 in report for this server
            except TypeError:
                report.write("{},0,0,0,0,0,0,0,0,0,0,0,0\n".format(srv))
except IOError:
    print("Can't open file for writting")
    sys.exit(2)

print("Done!")
