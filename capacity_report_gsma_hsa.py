#!/usr/bin/env python3
# K8S cluster resources allocation and usage
# Date: May 2017
# Author: Claudiu Tomescu
# e-mail: klau2005@tutanota.com

import re, sys, requests
from subprocess import getstatusoutput as get_stat

# convert full CPU resource value from k8s into milicpu format (eg. from 1 to 1000)
def conv_cpu_val(val):
    if not "m" in val:
        result = int(val) * 1000
    else:
        result = int(val.strip("m"))
    return result

# convert memory resource value from k8s from KB/GB into MB (eg. from 4046588Ki to 3951 or from 2Gi to 2048)
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
                value = data[metric_line].split("\t")[-1]
            # if we need memory size, search for the third line after the match
            elif metric == "memory_capacity":
                metric_line = i+3
                value = conv_mem_val(data[metric_line].split("\t")[-1])
        # search for the line that starts with "CPU Requests" to get resource usage
        elif re.match("^ *CPU Requests", data[i]):
            metric_line = i+2
            if metric == "cpu_requests":
                value = conv_cpu_val(data[metric_line].split()[0])
            elif metric == "cpu_requests_perc":
                value = data[metric_line].split()[1].strip("()").strip("%")
            elif metric == "cpu_limits":
                value = conv_cpu_val(data[metric_line].split()[2])
            elif metric == "cpu_limits_perc":
                value = data[metric_line].split()[3].strip("()").strip("%")
            elif metric == "mem_requests":
                value = conv_mem_val(data[metric_line].split()[4])
            elif metric == "mem_requests_perc":
                value = data[metric_line].split()[5].strip("()").strip("%")
            elif metric == "mem_limits":
                value = conv_mem_val(data[metric_line].split()[6])
            elif metric == "mem_limits_perc":
                value = data[metric_line].split()[7].strip("()").strip("%")
        i+=1
    return value

# create dictionary for storing final data to generate report from
report_dict = {}
# define empty dictionary to store nodes and raw metrics from kubectl describe command
nodes_dict = {}

# run kubectl command and get list of nodes
nodes_status = get_stat("kubectl get no | awk '!/NAME/{print $1}'")[0]
if nodes_status == 0:
    k8s_nodes_list = get_stat("kubectl get no | awk '!/NAME/{print $1}'")[1].split("\n")
    # populate nodes_dict
    for srv in k8s_nodes_list:
        nodes_dict[srv] = {}
else:
    print("kubectl command failed")
    sys.exit(2)

# get metrics for each node
for srv in nodes_dict.keys():
    comm = "kubectl describe no {}".format(srv)
    result = get_stat(comm)
    metrics_status = result[0]
    if metrics_status == 0:
        nodes_dict[srv] = result[1].split("\n")
    else:
        print("kubectl command failed")
        sys.exit(2)

# populate report dictionary with needed metrics
for srv in nodes_dict.keys():
    report_dict[srv] = {}

for srv in report_dict.keys():
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

# main function goes here
def main():
    # print the nodes and associated metrics in csv format
    header_line = "Server,CPUs number,Memory capacity(MB),CPU requests,CPU requests percent,CPU limits,\
        CPU limits percent,Memory requests(MB),Memory requests percent,Memory limits(MB),Memory limits percent"
    print(header_line)
    for srv in report_dict.keys():
        print("{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},{10}".format(srv, report_dict[srv]["CPUs number"], \
                report_dict[srv]["Memory capacity"], report_dict[srv]["CPU requests"], \
                report_dict[srv]["CPU requests percent"], report_dict[srv]["CPU limits"], \
                report_dict[srv]["CPU limits percent"], report_dict[srv]["Memory requests"], \
                report_dict[srv]["Memory requests percent"], report_dict[srv]["Memory limits"], \
                report_dict[srv]["Memory limits percent"]))

if __name__ == '__main__':
    main()
