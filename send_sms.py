#!/usr/bin/env python2.7
# Description: send SMS for each create/status/recovery critical JIRA ticket
# Author: Claudiu Tomescu
# E-mail: klau2005@gmail.com
# September 2016

import os, sys
import urllib
from datetime import datetime

# define variables
user = ""
passwd = ""
action = sys.argv[1]
project = sys.argv[2]
incident = sys.argv[3]
summary = sys.argv[4]
created = sys.argv[5][:16]
recovered = sys.argv[6][:16]
severity = sys.argv[7]
status = sys.argv[8]
# get only the city (Paris in this case) from the TZ env variable
tz = os.environ.get("TZ").split("/")[1]
log_file = "/home/runjira/scripts/logs/sms_log"
timestamp = str(datetime.now())

# define 2 dictionaries with Name:MSISDN pairs
mgmt_dict = {"abc": "123456789", "def": "987654321"}
osm_dict = {}
# and L1 backup mobile so they are aware if SMS sending fails
ot_mobile = ""

# list of recipients for SMS delivery
msisdn_list = ""
for key in mgmt_dict:
    msisdn_list += (mgmt_dict[key] + ",")
msisdn_list += ot_mobile

# function to compose the SMS message based on JIRA action (create incident, send status update or mark recovery)
def compose_sms_text(action_str):
    if action_str == "opened":
        sms_text = "New CRITICAL " + incident + " \"" + summary + "\" has been " + action_str + " for " + project + " at " + created + " " + tz + " time!"
    elif action_str == "restored":
        sms_text = "Critical ticket " + incident + " for " + project + " has been " + action_str.upper() + " at " + recovered + " " + tz + " time!"
    elif action_str == "status":
        sms_text = "Status for " + incident + " " + project + ": " + status
    else:
        sys.exit(7)
    # truncate SMS text to fit in 2 messages and write WARNING in log file
    if len(sms_text) > 306:
        sms_text = sms_text[:306]
        with open(log_file, "a+") as log:
            log.write("[" + timestamp + "] [WARNING] exceeded 2 messages for " + incident + " " + action + " step\n")
    return sms_text

def main():
    # double-check to see if the incident is critical
    if severity != "Critical":
        with open(log_file, "a+") as log:
            log.write("[" + timestamp + "] [WARNING] " + incident + " is not a critical incident\n")
        sys.exit(5)
    else:
        # compose the message body
        sms_text = compose_sms_text(action)
        # define the API URL and the required parameters
        url = "https://bulksms.vsms.net/eapi/submission/send_sms/2/2.0"
        params = urllib.urlencode({'username' : user, 'password' : passwd, 'message' : sms_text, 'msisdn' : msisdn_list, 'allow_concat_text_sms' : 1, 'concat_text_sms_max_parts' : 2})
        # open connection
        f = urllib.urlopen(url, params)
        stream = f.read()
        # get result code and message
        result = stream.split('|')
        status_code = result[0]
        status_string = result[1]
        # write the result in the log file
        with open(log_file, "a+") as log:
            if status_code != '0':
                log.write("[" + timestamp + "] [ERROR] could not send SMS for ticket " + incident + " " + action + " step [error: " + status_code + " " + status_string + "]\n")
            else:
                log.write("[" + timestamp + "] [SUCCESS] message sent for ticket " + incident + " " + action + " step [batch ID: " + result[2].strip("\n") + "]\n")
        f.close()

if __name__ == "__main__":
    main()
