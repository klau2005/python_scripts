#!/usr/bin/env python3
# List processes and their swap usage sorted by size
# Date: 2017-02-22
# Author: Claudiu Tomescu
# e-mail: klau2005@gmail.com

import os,sys,re

# first check we if use swap on this machine
try:
    with open("/proc/meminfo", "r") as memfile:
        for line in memfile:
            if re.match("SwapTotal", line):
                swap_total = int(line.split()[1].strip())
            elif re.match("SwapFree", line):
                swap_free = int(line.split()[1].strip())
except:
    print("Cannot open /proc/meminfo for reading\nexiting")
    sys.exit(1)

if (swap_total == swap_free):
    print("No swap used. Exiting...")
    sys.exit(0)

# get list of all running pids and add them to a list
pids = [pid for pid in os.listdir('/proc') if re.match("[0-9]+", pid)]

# define 2 dictionaries for storing pids and their swap/memory usage
swap_dict = {}
mem_dict = {}

for pid in pids:
    try:
        with open("/proc/" + pid + "/status", "r") as file:
            for line in file:
                if re.match("Name", line):
                    name = line.split()[1].strip()
                elif re.match("VmSwap", line):
                    size = int(line.split()[1].strip())
            swap_dict[pid + " - " + name] = size
    except FileNotFoundError:
        continue

# finally print the pids and swap used sorted by size
print("PID - process:\tsize")
for item in sorted(swap_dict, key=swap_dict.__getitem__):
    if swap_dict[item] != 0: #don't print those that use 0 swap
        print(item + ": " + str(swap_dict[item]) + " KB")

sys.exit(0)
