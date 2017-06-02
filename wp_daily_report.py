#!/usr/bin/env python3
# Description: generate WP daily report
# Author: Claudiu Tomescu
# E-mail: c.tomescu@oberthur.com
# September 2016

import sys, os, re
from datetime import datetime

# define the necessary variables, lists and dictionaries
se_file = "wp_reports/se.csv"
start_hour = 13
end_hour = 12
date_format = "%Y-%m-%d"
action_list = ["FACTORY_RESET", "PULL_CR_PERSO"]
se_list_temp = []
se_list = []
year_list = []
month_list = []
day_list = []
status_header = ["REQUESTED_DATE", "EUID", "ACTION", "COMPLETE_DATE", "HOUR", "MIN", "STATUS", "REMARKS", "SERVICE"]
oti_header = ["Hour"]
for n in range(start_hour, 24):
    oti_header.append(n)

for n in range(0, start_hour):
    oti_header.append(n)

failed_dict = {hour: [] for hour in oti_header[1:]}
OTI = {"Cards download": {hour: [] for hour in oti_header[1:]}, "Users terminated": {hour: [] for hour in oti_header[1:]}, "Failed download": {hour: [] for hour in oti_header[1:]}, 1: ["Number of users with successful card downloads"], 2: ["Number of terminated users"], 3: ["Number of cards successfully downloaded"], 4: ["Number of failed downloads"], 5: ["Number of expired card requests"]}

# define the functions
def get_value(name, item, pos=0):
    if name == "euid":
        value = int(item.split(";")[pos])
    elif name == "action":
        value = item.split(";")[4]
    elif name == "status":
        value = item.split(";")[6]
    elif name == "service":
        service = item.split(";")[8]
        value = re.sub(r" Mobile Credit", "", service)
    elif name == "date":
        value = item.split(";")[pos].split("T")[0]
    elif name == "year":
        value = int(item.split(";")[pos].split("-")[0])
    elif name == "month":
        value = int(item.split(";")[pos].split("-")[1])
    elif name == "day":
        value = int(item.split(";")[pos].split("-")[2].split("T")[0])
    elif name == "hour":
        value = int(item.split(";")[5].split("T")[1].split(":")[0])
    elif name == "minute":
        value = int(item.split(";")[5].split(":")[1].strip("Z"))
    else:
        print("Invalid name!")
        sys.exit(1)
    return value

def conv_status(status):
    if status == "OK":
        output = "Successful"
    elif status == "KO":
        output = "Failed"
    else:
        print("Unrecognized status!")
        sys.exit(1)
    return output

def compose_file_name(name):
    file_name = "wp_reports/%s_%d-%02d-%02d.csv" % (name, max(year_list), current_month, today)
    return file_name

# this function checks if an EUID is expired based on start and end dates of the request
def is_expired(item, start_pos, end_pos):
    start_date = datetime.strptime(get_value("date", item, start_pos), date_format)
    end_date = datetime.strptime(get_value("date", item, end_pos), date_format)
    delta = end_date - start_date
    if delta.days < 30:
        expired = False
    else:
        expired = True
    return expired

# function to extract only relevant fields from original csv file and replace ";" with ","
def conv_lines(line):
    new_line = re.sub(r"(^.*?;).*?;(.*?;).*?;(.*?;.*?;.*?;).*?;(.*?;).*$", "\\1\\2\\3\\4", line)
    final_line = re.sub(r";", ",", new_line)
    return final_line

# open the se.csv file and populate first list with the rows we care about
try:
    with open(se_file, "r") as se_file:
        for line in se_file:
            action = get_value("action", line)
            complete_date = line.split(";")[5]
            if action in action_list and complete_date != "":
                se_list_temp.append(line)
except FileNotFoundError:
    print("se.csv file not found")
    sys.exit(1)

# populate year, month and day lists
for item in se_list_temp:
    year = get_value("year", item, 5)
    month = get_value("month", item, 5)
    day = get_value("day", item, 5)
    if year not in year_list:
        year_list.append(year)
    if month not in month_list:
        month_list.append(month)
    if day not in day_list:
        day_list.append(day)

# check if the report contains the correct number of days data
if len(day_list) != 2:
    print("The report contains data for more/less than 2 days!")
    sys.exit(1)
# then we check which one is today/yesterday based on the number of months we have
elif len(month_list) == 1:
    today = max(day_list)
    yesterday = min(day_list)
    current_month = max(month_list)
elif len(month_list) == 2:
    today = min(day_list)
    yesterday = max(day_list)
    # then we check to see which one is the current/last month
    if len(year_list) == 1:
        current_month = max(month_list)
        last_month = min(month_list)
    elif len(year_list) == 2:
        current_month = min(month_list)
        last_month = max(month_list)
else:
    print("Unknown error!")
    sys.exit(1)

# here we sort the initial list
sorted_list = sorted(se_list_temp, key=lambda item: item.split(";")[5])

# we populate the second list, keeping only data for the hours we are reporting on
for item in sorted_list:
    day = get_value("day", item, 5)
    hour = get_value("hour", item)
    if day == yesterday and hour >= start_hour:
        se_list.append(item)
    elif day == today and hour <= end_hour:
        se_list.append(item)
    else:
        continue

# delete the temp lists, we will use the second from now on
del se_list_temp, sorted_list

# we populate the OTI dictionary
for item in se_list:
    euid = get_value("euid", item, 2)
    action = get_value("action", item)
    status = get_value("status", item)
    hour = get_value("hour", item)
    if action == action_list[1] and status == "OK":
        OTI["Cards download"][hour].append(euid)
    elif action == action_list[0] and status == "OK":
        OTI["Users terminated"][hour].append(euid)
    elif action == action_list[1] and status == "KO":
        OTI["Failed download"][hour].append(item.split(";")[0] + ";" + item.split(";")[2] + ";" + item.split(";")[5])
    else:
        continue

# and add more data to the same OTI dictionary
for hour in oti_header[1:]:
    users_ok = len(set(OTI["Cards download"][hour]))
    OTI[1].append(users_ok)
    reset_ok = len(OTI["Users terminated"][hour])
    OTI[2].append(reset_ok)
    cards_ok = len(OTI["Cards download"][hour])
    OTI[3].append(cards_ok)
    expired = 0
    for item in OTI["Failed download"][hour]:
        euid = get_value("euid", item, 1)
        if is_expired(item, 0, 2):
            expired += 1
        else:
            failed_dict[hour].append(euid)
    OTI[4].append(len(set(failed_dict[hour])))
    OTI[5].append(expired)

# compose oti file name for reporting day
oti_file = compose_file_name("oti")
# open oti file and write the data
with open(oti_file, "w") as oti:
    oti.write(str(oti_header).strip("[]") + "\n")
    for n in range(1, 6):
        oti.write(str(OTI[n]).strip("[]") + "\n")
    oti.write("\n" + "Failed cards\nHour,EUID\n")
    for key in failed_dict:
        if (len(failed_dict[key]) != 0):
            oti.write(str(key) + "," + str(set(failed_dict[key])).strip("{}") + "\n")

# compose status table file name for reporting day
status_file = compose_file_name("status_table")
# open status table file and write the data
with open(status_file, "w") as status_table:
    status_table.write(str(status_header).strip("[]") + "\n")
    for item in se_list:
        action = get_value("action", item)
        if is_expired(item, 0, 5):
            remark = "expired"
        else:
            remark = ""
        if action == action_list[1]:
            status_table.write(str(item.split(";")[0].strip("Z")) + "," + str(item.split(";")[2]) + "," + str(item.split(";")[4]) + "," + str(get_value("date", item, 5)) + "," + str(get_value("hour", item)) + "," + str(get_value("minute", item)) + "," + conv_status(get_value("status", item)) + "," + remark + "," + get_value("service", item) + "\n")

# we print the name of the created output files to be processed by php
print(oti_file)
print(status_file)

sys.exit(0)
