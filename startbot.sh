#!/bin/bash

# Backups the log file (true returned in case my.log does not exist yet)
cp my.log my.log.bak | true
# Removes the old log file
rm -f my.log

# Starts Nano with nohup - output is redirected to my.log
nohup python3 nano.py > my.log 2>&1&

# In case you need to kill the process, save_pid.txt is saved
echo $! > save_pid.txt
