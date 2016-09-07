#!/usr/bin/env python3
# Description: check BTRFS partition using FS native tools
# Author: Claudiu Tomescu
# E-mail: klau2005@gmail.com
# July 2016

import sys, re
from subprocess import getstatusoutput

if len(sys.argv) != 4:
    print("Usage: " + sys.argv[0] + " warning_threshold critical_threshold partition")
    sys.exit(3) # exit with UNKNOWN code

warn_threshold = int(sys.argv[1])
crit_threshold = int(sys.argv[2])
partition = sys.argv[3]
btrfs_df_com = "sudo btrfs filesystem df " + partition
btrfs_show_com = "sudo btrfs filesystem show " + partition

# function to display error in case of command failed
def btrfs_fail():
    print("BTRFS command failed! | 0")
    sys.exit(3) # exit with UNKNOWN code

# function to calculate values in MB from different human-readable values (for ex. from 25GiB)
def get_MB_val(val):
    if "GiB" in val:
        MB_val = float(val[:-3]) * 1073741824
        MB_val /= 1048576
    elif "MiB" in val:
        MB_val = float(val[:-3])
    elif "KiB" in val:
        MB_val = float(val[:-3]) * 1024
        MB_val /= 1048576
    else:
        MB_val = 1
    return MB_val

# run the 2 BTRFS commands and get the output
btrfs_df = getstatusoutput(btrfs_df_com)
if int(btrfs_df[0]) != 0:
    btrfs_fail()

df_output = btrfs_df[1].split("\n")

btrfs_show = getstatusoutput(btrfs_show_com)
if int(btrfs_show[0]) != 0:
    btrfs_fail()

show_output = btrfs_show[1].split("\n")

# define an array which we'll use for storing values from the BTRFS DF command
df_array = {}
for line in df_output:
    if 'used=0.00' in line:
        continue
    else:
        name = line.split()[0].strip(",")
        tot_df_str = line.split()[2].split("=")[1].strip(",")
        tot_df_MB = get_MB_val(tot_df_str)
        used_df_str = line.split()[3].split("=")[1].strip(",")
        used_df_MB = get_MB_val(used_df_str)
        free_df_MB = tot_df_MB - used_df_MB
        df_array[name] = {"Total MB": tot_df_MB, "Used MB": used_df_MB, "Free MB": free_df_MB}

for line in show_output:
    if "Total devices" in line:
        tot_used_str = line.split()[6]
        tot_used_MB = get_MB_val(tot_used_str)
    elif "devid" in line:
        tot_str = line.split()[3]
        tot_MB = get_MB_val(tot_str)
        tot_alloc_str = line.split()[5]
        tot_alloc_MB = get_MB_val(tot_alloc_str)
        tot_unalloc_MB = tot_MB - tot_alloc_MB

tot_used_perc = '%.2f' % (tot_used_MB / tot_MB * 100)
tot_free_MB = tot_MB - tot_used_MB
tot_free_perc = '%.2f' % (tot_free_MB / tot_MB * 100)
used_perf_space = '%sMB' % (int(tot_used_MB))
warn_perf_space = int(tot_MB * warn_threshold / 100)
crit_perf_space = int(tot_MB * crit_threshold / 100)
tot_perf_space = int(tot_MB)

# compose plugin message
output = partition + " - TOTAL: " + str(int(tot_MB)) + "MB USED: " + str(int(tot_used_MB)) + "MB(" + str(tot_used_perc) + "%) FREE: " + str(int(tot_free_MB)) + "MB(" + str(tot_free_perc) + "%)"
for key in df_array:
    output += "; " + key + " - Allocated: " + str(int(df_array[key]['Total MB'])) + "MB Used: " + str(int(df_array[key]['Used MB'])) + "MB"

# compose perf data message
perf_data = partition + "=" + used_perf_space + ";" + str(warn_perf_space) + ";" + str(crit_perf_space) + ";" + "0" + ";" + str(tot_perf_space)
for key in df_array:
    perf_data += " " + key + "=" + str(int(df_array[key]['Used MB'])) + "MB;" + str(warn_perf_space) + ";" + str(crit_perf_space) + ";" + "0" + ";" + str(tot_perf_space)

# initialize crit and warn variables and increase their counter if we find space issues
crit_counter = 0
warn_counter = 0
for key in df_array:
    if (df_array[key]['Used MB'] / (df_array[key]['Total MB'] + tot_unalloc_MB) * 100) >= crit_threshold:
        crit_counter += 1
    elif (df_array[key]['Used MB'] / (df_array[key]['Total MB'] + tot_unalloc_MB) * 100) >= warn_threshold:
        warn_counter += 1

# set message and exit status based on disk space state
if (crit_counter > 0):
    print("DISK CRITICAL - " + output + " | " + perf_data)
    sys.exit(2) # exit with CRITICAL code
elif (warn_counter > 0):
    print("DISK WARNING - " + output + " | " + perf_data)
    sys.exit(1) # exit with WARNING code
else:
    print("DISK OK - " + output + " | " + perf_data)
    sys.exit(0) # exit with OK code

